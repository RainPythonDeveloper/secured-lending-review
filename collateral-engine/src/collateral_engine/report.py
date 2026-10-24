"""The valuation report: what the officer console shows and the API returns.

Money is Decimal and serialises as a decimal string, as in the Georgian Open Banking API.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from collateral_engine.domain import (
    BuildingStatus,
    ClaimStatus,
    Condition,
    Currency,
    District,
    ExchangeRate,
    SubjectProperty,
)
from collateral_engine.flags import Flag, Recommendation
from collateral_engine.hedonic import AdjustmentGroup
from collateral_engine.nbg_rules import ValuationLimits
from collateral_engine.photos import PhotoQualityIssue
from collateral_engine.vision import VisionConfidence, VisionFailure


class _Report(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AppraisalPosition(StrEnum):
    WITHIN_RANGE = "WITHIN_RANGE"
    ABOVE_RANGE = "ABOVE_RANGE"
    BELOW_RANGE = "BELOW_RANGE"


class AdjustmentTier(StrEnum):
    """NBG Order 84/04 Art. 4(5)(b): gross adjustment within 25%, or up to 35% when justified."""

    WITHIN_LIMITS = "WITHIN_LIMITS"
    JUSTIFICATION_REQUIRED = "JUSTIFICATION_REQUIRED"


class LendingValueBasis(StrEnum):
    """Which value the LTV is computed on; always the more conservative one available."""

    MODEL_RANGE_LOW = "MODEL_RANGE_LOW"
    LICENSED_APPRAISAL = "LICENSED_APPRAISAL"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"


class ComparableRow(_Report):
    sale_id: str
    sale_date: date
    district: District
    latitude: float
    longitude: float
    distance_km: float
    total_area_m2: float
    land_area_m2: float | None = None
    floor: int
    building_floors: int
    building_status: BuildingStatus
    condition: Condition
    price_usd: Decimal
    price_per_m2_usd: Decimal
    adjustments: dict[AdjustmentGroup, float]
    gross_adjustment: float
    adjusted_price_per_m2_usd: Decimal
    weight: float


class MarketValuation(_Report):
    valued_condition: Condition
    price_per_m2_usd: Decimal
    market_value_usd: Decimal
    range_low_usd: Decimal
    range_high_usd: Decimal
    range_coverage: float
    hedonic_value_usd: Decimal
    model_disagreement: float
    search_radius_km: float
    was_radius_widened: bool
    adjustment_tier: AdjustmentTier
    valuation_limits: ValuationLimits
    comparables: list[ComparableRow]


class PhotoFinding(_Report):
    sha256: str
    width_px: int | None
    height_px: int | None
    quality_issues: list[PhotoQualityIssue]
    shows_apartment_interior: bool | None
    contains_people: bool | None
    observed_condition: Condition | None
    vision_confidence: VisionConfidence | None
    visible_evidence: list[str]
    vision_failure: VisionFailure | None
    seen_in_other_applications: list[str]


class ConditionVerification(_Report):
    declared: Condition
    observed: Condition | None
    status: ClaimStatus
    valued_condition: Condition
    counted_photos: int
    agreement_share: float | None
    photos_submitted: int
    photos_required: int
    rules_version: str


class AppraisalCheck(_Report):
    appraised_value: Decimal
    currency: Currency
    appraised_value_usd: Decimal
    position: AppraisalPosition
    deviation_from_estimate: float


class LtvCheck(_Report):
    nbg_rules_version: str
    loan_amount: Decimal
    loan_currency: Currency
    lending_value_usd: Decimal
    lending_value_basis: LendingValueBasis
    completion_risk_factor: Decimal | None = None
    lending_value_in_loan_currency: Decimal
    ltv_limit: Decimal
    ltv_ratio: Decimal
    is_within_limit: bool
    max_loan_amount: Decimal
    gel_appreciation_stress: Decimal | None
    stressed_ltv_ratio: Decimal | None
    is_within_limit_under_stress: bool | None


class ValuationReport(_Report):
    valuation_id: str
    application_id: str
    valuation_date: date
    model_version: str
    policy_version: str
    market_data_source: str
    subject: SubjectProperty
    usd_rate: ExchangeRate
    valuation: MarketValuation | None
    condition: ConditionVerification
    photos: list[PhotoFinding]
    # The vision model that described the photos; None when photo analysis is off.
    vision_model: str | None
    appraisal: AppraisalCheck | None
    ltv: LtvCheck | None
    flags: list[Flag]
    recommendation: Recommendation
