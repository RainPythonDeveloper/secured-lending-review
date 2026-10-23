"""Reason codes raised during an assessment and how they combine into a recommendation.

The recommendation is advice to the loan officer. There is no automatic rejection: the strongest
outcome is a physical inspection by a licensed valuer.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReasonCode(StrEnum):
    INSUFFICIENT_COMPARABLES = "INSUFFICIENT_COMPARABLES"
    COMPARABLES_WIDENED_RADIUS = "COMPARABLES_WIDENED_RADIUS"
    ADJUSTMENT_JUSTIFICATION_REQUIRED = "ADJUSTMENT_JUSTIFICATION_REQUIRED"
    MODEL_DISAGREEMENT = "MODEL_DISAGREEMENT"
    APPRAISAL_ABOVE_RANGE = "APPRAISAL_ABOVE_RANGE"
    APPRAISAL_BELOW_RANGE = "APPRAISAL_BELOW_RANGE"
    CONDITION_PARTLY_CONFIRMED = "CONDITION_PARTLY_CONFIRMED"
    CONDITION_CONTRADICTED = "CONDITION_CONTRADICTED"
    CONDITION_INCONCLUSIVE = "CONDITION_INCONCLUSIVE"
    CONDITION_NOT_VERIFIED = "CONDITION_NOT_VERIFIED"
    TOO_FEW_PHOTOS = "TOO_FEW_PHOTOS"
    PHOTO_QUALITY_ISSUES = "PHOTO_QUALITY_ISSUES"
    PHOTOS_WITH_PEOPLE_EXCLUDED = "PHOTOS_WITH_PEOPLE_EXCLUDED"
    NEAR_DUPLICATE_PHOTOS = "NEAR_DUPLICATE_PHOTOS"
    PHOTO_SEEN_IN_OTHER_APPLICATION = "PHOTO_SEEN_IN_OTHER_APPLICATION"
    VISION_UNAVAILABLE = "VISION_UNAVAILABLE"
    OFF_PLAN_COMPLETION_OVERDUE = "OFF_PLAN_COMPLETION_OVERDUE"
    OFF_PLAN_AGREEMENT_NOT_REGISTERED = "OFF_PLAN_AGREEMENT_NOT_REGISTERED"
    OFF_PLAN_LONG_COMPLETION = "OFF_PLAN_LONG_COMPLETION"
    OFF_PLAN_STAGE_DISCOUNT = "OFF_PLAN_STAGE_DISCOUNT"
    LTV_ABOVE_LIMIT = "LTV_ABOVE_LIMIT"
    LTV_ABOVE_LIMIT_UNDER_FX_STRESS = "LTV_ABOVE_LIMIT_UNDER_FX_STRESS"


class Severity(StrEnum):
    INFO = "info"
    REVIEW = "review"
    PHYSICAL_INSPECTION = "physical_inspection"


class Recommendation(StrEnum):
    ACCEPT_VALUATION = "ACCEPT_VALUATION"
    OFFICER_REVIEW = "OFFICER_REVIEW"
    PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION"


class Flag(BaseModel):
    """A reason code with the values its message needs, for example a deviation in percent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ReasonCode
    severity: Severity
    params: dict[str, str] = {}


_RECOMMENDATION_BY_SEVERITY = {
    Severity.INFO: Recommendation.ACCEPT_VALUATION,
    Severity.REVIEW: Recommendation.OFFICER_REVIEW,
    Severity.PHYSICAL_INSPECTION: Recommendation.PHYSICAL_INSPECTION,
}
_SEVERITY_ORDER = (Severity.INFO, Severity.REVIEW, Severity.PHYSICAL_INSPECTION)


def recommend(flags: list[Flag]) -> Recommendation:
    """The most severe flag decides; an assessment without flags is accepted."""
    worst = max((flag.severity for flag in flags), key=_SEVERITY_ORDER.index, default=Severity.INFO)
    return _RECOMMENDATION_BY_SEVERITY[worst]
