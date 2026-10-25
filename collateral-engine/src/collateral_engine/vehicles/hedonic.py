"""Hedonic model of one make and model: log price on age, mileage and the Georgian risk factors.

Its coefficients serve as adjustment rates in the comparables grid and give the depreciation used
to project the value to the end of the loan.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from collateral_engine.hedonic import AVERAGE_DAYS_PER_MONTH
from collateral_engine.vehicles.domain import FuelType, SteeringSide
from collateral_engine.vehicles.policy import VehicleHedonicPolicy
from collateral_engine.vehicles.report import VehicleAdjustmentGroup

MIN_SALES_TO_FIT = 30
# Keeps log(mileage) finite for a new vehicle with almost no kilometres.
MILEAGE_OFFSET_KM = 1000.0

FEATURE_LAYOUT: tuple[tuple[str, VehicleAdjustmentGroup | None], ...] = (
    ("intercept", None),
    ("age_years", VehicleAdjustmentGroup.AGE),
    ("log_mileage_km", VehicleAdjustmentGroup.MILEAGE),
    ("has_accident_history", VehicleAdjustmentGroup.ACCIDENT),
    ("right_hand_drive", VehicleAdjustmentGroup.STEERING),
    ("not_customs_cleared", VehicleAdjustmentGroup.CUSTOMS),
    ("gas_conversion", VehicleAdjustmentGroup.FUEL),
    ("months_before_valuation", VehicleAdjustmentGroup.TIME),
)
FEATURE_NAMES = tuple(name for name, _ in FEATURE_LAYOUT)
FEATURE_INDICES_BY_GROUP = {
    group: [index for index, (_, owner) in enumerate(FEATURE_LAYOUT) if owner is group]
    for group in VehicleAdjustmentGroup
}


class InsufficientVehicleDataError(ValueError):
    """Too few sales of the make and model to fit its hedonic model."""


def log_mileage(mileage_km: np.ndarray | float) -> np.ndarray:
    return np.log(np.asarray(mileage_km, dtype=float) + MILEAGE_OFFSET_KM)


def encode_vehicle_features(frame: pd.DataFrame, valuation_date: date) -> np.ndarray:
    """One row per sale; sale_date is the valuation date for the vehicle being valued."""
    sale_dates = pd.to_datetime(frame["sale_date"])
    days_before = (pd.Timestamp(valuation_date) - sale_dates).dt.days.to_numpy(float)
    return np.column_stack(
        [
            np.ones(len(frame)),
            (sale_dates.dt.year - frame["production_year"]).to_numpy(float),
            log_mileage(frame["mileage_km"].to_numpy(float)),
            frame["has_accident_history"].to_numpy(float),
            (frame["steering"] == SteeringSide.RIGHT).to_numpy(float),
            (~frame["is_customs_cleared"].astype(bool)).to_numpy(float),
            (frame["fuel"] == FuelType.PETROL_GAS).to_numpy(float),
            days_before / AVERAGE_DAYS_PER_MONTH,
        ]
    )


@dataclass(frozen=True)
class VehicleHedonicModel:
    coefficients: np.ndarray
    sales_used: int

    def coefficient(self, feature_name: str) -> float:
        return float(self.coefficients[FEATURE_NAMES.index(feature_name)])

    def predict_price_usd(self, frame: pd.DataFrame, valuation_date: date) -> np.ndarray:
        return np.exp(encode_vehicle_features(frame, valuation_date) @ self.coefficients)

    def group_log_adjustments(
        self, subject_features: np.ndarray, comparable_features: np.ndarray
    ) -> dict[VehicleAdjustmentGroup, np.ndarray]:
        """Log change that turns each comparable's price into the subject's, by group."""
        contributions = (subject_features - comparable_features) * self.coefficients
        return {
            group: contributions[:, indices].sum(axis=1)
            for group, indices in FEATURE_INDICES_BY_GROUP.items()
        }


def fit_vehicle_hedonic_model(
    sales: pd.DataFrame, valuation_date: date, policy: VehicleHedonicPolicy
) -> VehicleHedonicModel:
    if len(sales) < MIN_SALES_TO_FIT:
        raise InsufficientVehicleDataError(
            f"{len(sales)} sales of the model before {valuation_date}; "
            f"at least {MIN_SALES_TO_FIT} are needed"
        )
    features = encode_vehicle_features(sales, valuation_date)
    log_price = np.log(sales["price_usd"].to_numpy(float))
    # The intercept stays unpenalised; rare factors such as right-hand drive shrink towards zero.
    penalty = np.diag([0.0] + [policy.ridge_penalty * len(sales)] * (features.shape[1] - 1))
    coefficients = np.linalg.solve(features.T @ features + penalty, features.T @ log_price)
    return VehicleHedonicModel(coefficients, len(sales))
