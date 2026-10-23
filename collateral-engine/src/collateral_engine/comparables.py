"""Choosing comparable sales for a flat, as a valuer would: close, recent and similar in size."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Self

import numpy as np
import pandas as pd

from collateral_engine.domain import BuildingStatus, Condition, District, SubjectProperty
from collateral_engine.geo import haversine_km
from collateral_engine.hedonic import AVERAGE_DAYS_PER_MONTH
from collateral_engine.market import MarketData
from collateral_engine.policy import ComparablesPolicy
from collateral_engine.reference import metro_distance_km
from collateral_engine.report import AdjustmentTier


class InsufficientComparablesError(Exception):
    def __init__(self, found: int, required: int, radius_km: float) -> None:
        super().__init__(
            f"{found} comparable sales within {radius_km} km; at least {required} are needed"
        )
        self.found = found
        self.required = required
        self.radius_km = radius_km


@dataclass(frozen=True)
class PropertyFeatures:
    """What the valuation uses about a flat; the condition is the one the evidence supports."""

    district: District
    latitude: float
    longitude: float
    total_area_m2: float
    floor: int
    building_floors: int
    building_status: BuildingStatus
    condition: Condition

    @classmethod
    def of_subject(cls, subject: SubjectProperty, condition: Condition) -> Self:
        return cls(
            district=subject.district,
            latitude=subject.latitude,
            longitude=subject.longitude,
            total_area_m2=float(subject.total_area_m2),
            floor=subject.floor,
            building_floors=subject.building_floors,
            building_status=subject.building_status,
            condition=condition,
        )

    @classmethod
    def of_sale(cls, sale: pd.Series) -> Self:
        return cls(
            district=sale["district"],
            latitude=sale["latitude"],
            longitude=sale["longitude"],
            total_area_m2=sale["total_area_m2"],
            floor=sale["floor"],
            building_floors=sale["building_floors"],
            building_status=sale["building_status"],
            condition=sale["condition"],
        )

    def to_frame(self, valuation_date: date) -> pd.DataFrame:
        """One row in the market schema, as if the flat sold on the valuation date."""
        metro_km = metro_distance_km(np.array([self.latitude]), np.array([self.longitude]))
        row = {
            "district": self.district,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "total_area_m2": self.total_area_m2,
            "floor": self.floor,
            "building_floors": self.building_floors,
            "building_status": self.building_status,
            "condition": self.condition,
            "sale_date": pd.Timestamp(valuation_date),
            "metro_distance_km": float(metro_km[0]),
        }
        return pd.DataFrame([row])


@dataclass(frozen=True)
class ComparableSelection:
    sales: pd.DataFrame
    search_radius_km: float
    was_radius_widened: bool
    adjustment_tier: AdjustmentTier = AdjustmentTier.WITHIN_LIMITS


# Returns, per candidate, whether its adjustments are within the limits and within the
# justified limits.
type AdjustmentScreen = Callable[[pd.DataFrame], tuple[np.ndarray, np.ndarray]]


@dataclass(frozen=True)
class AdmissionRule:
    """Which candidates may serve as comparables, and how many are needed."""

    screen: AdjustmentScreen
    required_count: int


def select_comparables(
    subject: PropertyFeatures,
    market: MarketData,
    valuation_date: date,
    policy: ComparablesPolicy,
    admission: AdmissionRule,
    excluded_sale_id: str | None = None,
) -> ComparableSelection:
    """Uses only sales before the valuation date, so a valuation never sees the future.

    Sales whose adjustments stay within the limits come first; only if there are too few of them
    are sales within the justified limits used, and only then is the radius widened.
    """
    candidates = _eligible_candidates(subject, market, valuation_date, policy, excluded_sale_id)
    justified_found = 0
    for radius_km in (policy.search_radius_km, policy.widened_radius_km):
        within_radius = candidates[candidates["distance_km"] <= radius_km]
        within_limits, within_justified = admission.screen(within_radius)
        justified_found = int(within_justified.sum())
        tiers = (
            (within_limits, AdjustmentTier.WITHIN_LIMITS),
            (within_justified, AdjustmentTier.JUSTIFICATION_REQUIRED),
        )
        for admitted, tier in tiers:
            if admitted.sum() >= admission.required_count:
                return ComparableSelection(
                    sales=_closest_matches(within_radius[admitted], subject, radius_km, policy),
                    search_radius_km=radius_km,
                    was_radius_widened=radius_km != policy.search_radius_km,
                    adjustment_tier=tier,
                )
    raise InsufficientComparablesError(
        justified_found, admission.required_count, policy.widened_radius_km
    )


def _eligible_candidates(
    subject: PropertyFeatures,
    market: MarketData,
    valuation_date: date,
    policy: ComparablesPolicy,
    excluded_sale_id: str | None,
) -> pd.DataFrame:
    sales = market.sales
    age_days = (pd.Timestamp(valuation_date) - sales["sale_date"]).dt.days
    area_ratio = sales["total_area_m2"] / subject.total_area_m2
    is_eligible = (
        (age_days > 0)
        & (age_days <= policy.max_age_months * AVERAGE_DAYS_PER_MONTH)
        & (area_ratio >= 1 / policy.max_area_ratio)
        & (area_ratio <= policy.max_area_ratio)
        & (sales["sale_id"] != excluded_sale_id)
    )
    eligible = sales[is_eligible]
    distances = haversine_km(
        subject.latitude,
        subject.longitude,
        eligible["latitude"].to_numpy(),
        eligible["longitude"].to_numpy(),
    )
    return eligible.assign(distance_km=distances, age_days=age_days[is_eligible])


def _closest_matches(
    within_radius: pd.DataFrame,
    subject: PropertyFeatures,
    radius_km: float,
    policy: ComparablesPolicy,
) -> pd.DataFrame:
    max_age_days = policy.max_age_months * AVERAGE_DAYS_PER_MONTH
    dissimilarity = (
        within_radius["distance_km"] / radius_km
        + within_radius["age_days"] / max_age_days
        + np.abs(np.log(within_radius["total_area_m2"] / subject.total_area_m2))
    )
    return within_radius.assign(dissimilarity=dissimilarity).nsmallest(
        policy.max_count, "dissimilarity"
    )
