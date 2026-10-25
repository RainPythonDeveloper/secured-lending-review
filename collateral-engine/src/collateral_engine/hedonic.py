"""Hedonic regression of the log price of a square metre on the characteristics of a flat.

The coefficients serve twice: as adjustment rates in the comparable-sales grid, and as an
independent challenger estimate of the same flat.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np
import pandas as pd

from collateral_engine.domain import BuildingStatus, Condition, District
from collateral_engine.market import MarketData
from collateral_engine.policy import HedonicPolicy

AVERAGE_DAYS_PER_MONTH = 30.44
MIN_SALES_TO_FIT = 50
REFERENCE_CONDITION = Condition.NEWLY_RENOVATED
REFERENCE_BUILDING_STATUS = BuildingStatus.NEW_BUILDING


class InsufficientMarketDataError(Exception):
    """Too few sales to estimate the hedonic model."""


class AdjustmentGroup(StrEnum):
    TIME = "time"
    LOCATION = "location"
    CONDITION = "condition"
    BUILDING_STATUS = "building_status"
    FLOOR = "floor"
    SIZE = "size"
    LAND = "land"


def _feature_layout() -> tuple[tuple[str, AdjustmentGroup | None], ...]:
    features: list[tuple[str, AdjustmentGroup | None]] = [("intercept", None)]
    features += [(f"district:{district}", AdjustmentGroup.LOCATION) for district in District]
    features += [
        (f"condition:{condition}", AdjustmentGroup.CONDITION)
        for condition in Condition
        if condition is not REFERENCE_CONDITION
    ]
    features += [
        (f"building_status:{status}", AdjustmentGroup.BUILDING_STATUS)
        for status in BuildingStatus
        if status is not REFERENCE_BUILDING_STATUS
    ]
    features += [
        ("first_floor", AdjustmentGroup.FLOOR),
        ("top_floor", AdjustmentGroup.FLOOR),
        ("log_area_m2", AdjustmentGroup.SIZE),
        ("log_land_area_m2", AdjustmentGroup.LAND),
        ("metro_distance_km", AdjustmentGroup.LOCATION),
        ("sale_age_months", AdjustmentGroup.TIME),
    ]
    return tuple(features)


FEATURE_LAYOUT = _feature_layout()
FEATURE_NAMES = tuple(name for name, _ in FEATURE_LAYOUT)
FEATURE_INDICES_BY_GROUP = {
    group: [
        index for index, (_, feature_group) in enumerate(FEATURE_LAYOUT) if feature_group is group
    ]
    for group in AdjustmentGroup
}


def encode_features(
    frame: pd.DataFrame, valuation_date: date, metro_distance_cap_km: float
) -> np.ndarray:
    """One row per flat, columns in FEATURE_NAMES order."""
    floors = frame["floor"].to_numpy()
    building_floors = frame["building_floors"].to_numpy()
    sale_age_days = (pd.Timestamp(valuation_date) - frame["sale_date"]).dt.days.to_numpy()
    columns = [np.ones(len(frame))]
    columns += [(frame["district"] == district).to_numpy(float) for district in District]
    columns += [
        (frame["condition"] == condition).to_numpy(float)
        for condition in Condition
        if condition is not REFERENCE_CONDITION
    ]
    columns += [
        (frame["building_status"] == status).to_numpy(float)
        for status in BuildingStatus
        if status is not REFERENCE_BUILDING_STATUS
    ]
    columns += [
        (floors == 1).astype(float),
        ((floors == building_floors) & (building_floors > 1)).astype(float),
        np.log(frame["total_area_m2"].to_numpy(float)),
        # Flats have no land; log(1) = 0 keeps the feature neutral for them.
        np.log(frame["land_area_m2"].fillna(1.0).to_numpy(float)),
        np.minimum(frame["metro_distance_km"].to_numpy(float), metro_distance_cap_km),
        sale_age_days / AVERAGE_DAYS_PER_MONTH,
    ]
    return np.column_stack(columns)


@dataclass(frozen=True)
class HedonicModel:
    coefficients: np.ndarray
    sales_used: int
    metro_distance_cap_km: float

    def coefficient(self, feature_name: str) -> float:
        return float(self.coefficients[FEATURE_NAMES.index(feature_name)])

    def predict_price_per_m2_usd(self, frame: pd.DataFrame, valuation_date: date) -> np.ndarray:
        features = encode_features(frame, valuation_date, self.metro_distance_cap_km)
        return np.exp(features @ self.coefficients)

    def group_log_adjustments(
        self, subject_features: np.ndarray, comparable_features: np.ndarray
    ) -> dict[AdjustmentGroup, np.ndarray]:
        """Log change that turns each comparable's price into the subject's, by group."""
        contributions = (subject_features - comparable_features) * self.coefficients
        return {
            group: contributions[:, indices].sum(axis=1)
            for group, indices in FEATURE_INDICES_BY_GROUP.items()
        }


def fit_hedonic_model(
    market: MarketData, valuation_date: date, policy: HedonicPolicy
) -> HedonicModel:
    if len(market) < MIN_SALES_TO_FIT:
        raise InsufficientMarketDataError(
            f"{len(market)} sales before {valuation_date}; at least {MIN_SALES_TO_FIT} are needed"
        )
    features = encode_features(market.sales, valuation_date, policy.metro_distance_cap_km)
    log_price = np.log(market.sales["price_per_m2_usd"].to_numpy())
    # The intercept stays unpenalised, so a district without sales falls back to the city level.
    penalty = np.diag([0.0] + [policy.ridge_penalty * len(market)] * (features.shape[1] - 1))
    coefficients = np.linalg.solve(features.T @ features + penalty, features.T @ log_price)
    return HedonicModel(coefficients, len(market), policy.metro_distance_cap_km)
