"""Turns the parts of an assessment into reason codes; severities come from the policy file."""

from collateral_engine.comparables import InsufficientComparablesError
from collateral_engine.domain import ClaimStatus
from collateral_engine.flags import Flag, ReasonCode
from collateral_engine.policy import ValuationPolicy
from collateral_engine.report import (
    AdjustmentTier,
    AppraisalCheck,
    AppraisalPosition,
    ConditionVerification,
    LtvCheck,
    MarketValuation,
    PhotoFinding,
)
from collateral_engine.vision import VisionFailure

type FlagSpec = tuple[ReasonCode, dict[str, str]]

_CONDITION_REASONS = {
    ClaimStatus.PARTLY: ReasonCode.CONDITION_PARTLY_CONFIRMED,
    ClaimStatus.CONTRADICTED: ReasonCode.CONDITION_CONTRADICTED,
    ClaimStatus.INCONCLUSIVE: ReasonCode.CONDITION_INCONCLUSIVE,
    ClaimStatus.NOT_VERIFIED: ReasonCode.CONDITION_NOT_VERIFIED,
}


def _percent(fraction: float) -> str:
    return f"{abs(fraction) * 100:.1f}"


def valuation_findings(
    valuation: MarketValuation | None,
    shortage: InsufficientComparablesError | None,
    policy: ValuationPolicy,
) -> list[FlagSpec]:
    if valuation is None:
        found = shortage.found if shortage else 0
        radius = shortage.radius_km if shortage else policy.comparables.widened_radius_km
        return [
            (ReasonCode.INSUFFICIENT_COMPARABLES, {"found": str(found), "radius_km": str(radius)})
        ]
    findings: list[FlagSpec] = []
    if valuation.was_radius_widened:
        findings.append(
            (ReasonCode.COMPARABLES_WIDENED_RADIUS, {"radius_km": str(valuation.search_radius_km)})
        )
    if valuation.adjustment_tier is AdjustmentTier.JUSTIFICATION_REQUIRED:
        findings.append((ReasonCode.ADJUSTMENT_JUSTIFICATION_REQUIRED, _gross_params(valuation)))
    if valuation.model_disagreement > policy.review.max_model_disagreement:
        findings.append(
            (ReasonCode.MODEL_DISAGREEMENT, {"percent": _percent(valuation.model_disagreement)})
        )
    return findings


def _gross_params(valuation: MarketValuation) -> dict[str, str]:
    limits = valuation.valuation_limits
    largest = max(row.gross_adjustment for row in valuation.comparables)
    return {
        "gross": _percent(largest),
        "limit": _percent(limits.max_gross_adjustment),
        "justified_limit": _percent(limits.max_gross_adjustment_justified),
    }


def condition_findings(condition: ConditionVerification) -> list[FlagSpec]:
    findings: list[FlagSpec] = []
    required = str(condition.photos_required)
    if 0 < condition.photos_submitted < condition.photos_required:
        findings.append(
            (
                ReasonCode.TOO_FEW_PHOTOS,
                {"count": str(condition.photos_submitted), "required": required},
            )
        )
    reason = _CONDITION_REASONS.get(condition.status)
    if reason is None:
        return findings
    observed = condition.observed.value if condition.observed else ""
    params = {"declared": condition.declared.value, "observed": observed, "required": required}
    return [*findings, (reason, params)]


def photo_findings(photos: list[PhotoFinding], near_duplicate_pair_count: int) -> list[FlagSpec]:
    counts = {
        ReasonCode.PHOTO_QUALITY_ISSUES: sum(1 for photo in photos if photo.quality_issues),
        ReasonCode.PHOTOS_WITH_PEOPLE_EXCLUDED: sum(1 for photo in photos if photo.contains_people),
        ReasonCode.NEAR_DUPLICATE_PHOTOS: near_duplicate_pair_count,
        ReasonCode.VISION_UNAVAILABLE: sum(
            1
            for photo in photos
            if photo.vision_failure not in (None, VisionFailure.NOT_CONFIGURED)
        ),
    }
    findings: list[FlagSpec] = [
        (reason, {"count": str(count)}) for reason, count in counts.items() if count
    ]
    other_applications = sorted(
        {application for photo in photos for application in photo.seen_in_other_applications}
    )
    if other_applications:
        findings.append(
            (
                ReasonCode.PHOTO_SEEN_IN_OTHER_APPLICATION,
                {"applications": ", ".join(other_applications)},
            )
        )
    return findings


def appraisal_findings(appraisal: AppraisalCheck | None) -> list[FlagSpec]:
    if appraisal is None or appraisal.position is AppraisalPosition.WITHIN_RANGE:
        return []
    reason = (
        ReasonCode.APPRAISAL_ABOVE_RANGE
        if appraisal.position is AppraisalPosition.ABOVE_RANGE
        else ReasonCode.APPRAISAL_BELOW_RANGE
    )
    return [(reason, {"percent": _percent(appraisal.deviation_from_estimate)})]


def ltv_findings(ltv: LtvCheck | None) -> list[FlagSpec]:
    if ltv is None:
        return []
    limit = _percent(float(ltv.ltv_limit))
    if not ltv.is_within_limit:
        params = {
            "ltv": _percent(float(ltv.ltv_ratio)),
            "limit": limit,
            "max_loan": f"{ltv.max_loan_amount:,.2f}",
            "currency": ltv.loan_currency.value,
        }
        return [(ReasonCode.LTV_ABOVE_LIMIT, params)]
    if ltv.is_within_limit_under_stress is False and ltv.stressed_ltv_ratio is not None:
        params = {
            "ltv": _percent(float(ltv.stressed_ltv_ratio)),
            "limit": limit,
            "stress": _percent(float(ltv.gel_appreciation_stress or 0)),
        }
        return [(ReasonCode.LTV_ABOVE_LIMIT_UNDER_FX_STRESS, params)]
    return []


def to_flags(findings: list[FlagSpec], policy: ValuationPolicy) -> list[Flag]:
    return [
        Flag(code=reason, severity=policy.flag_severity[reason], params=params)
        for reason, params in findings
    ]
