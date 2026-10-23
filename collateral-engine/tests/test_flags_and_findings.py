from decimal import Decimal

import pytest

from collateral_engine.comparables import InsufficientComparablesError
from collateral_engine.domain import ClaimStatus, Condition, Currency
from collateral_engine.findings import (
    appraisal_findings,
    condition_findings,
    ltv_findings,
    photo_findings,
    to_flags,
    valuation_findings,
)
from collateral_engine.flags import Flag, ReasonCode, Recommendation, Severity, recommend
from collateral_engine.report import (
    AppraisalCheck,
    AppraisalPosition,
    ConditionVerification,
    LendingValueBasis,
    LtvCheck,
    PhotoFinding,
)
from collateral_engine.vision import VisionFailure


def flag(severity: Severity) -> Flag:
    return Flag(code=ReasonCode.PHOTO_QUALITY_ISSUES, severity=severity)


@pytest.mark.parametrize(
    ("severities", "recommendation"),
    [
        ([], Recommendation.ACCEPT_VALUATION),
        ([Severity.INFO], Recommendation.ACCEPT_VALUATION),
        ([Severity.INFO, Severity.REVIEW], Recommendation.OFFICER_REVIEW),
        ([Severity.REVIEW, Severity.PHYSICAL_INSPECTION], Recommendation.PHYSICAL_INSPECTION),
    ],
)
def test_most_severe_flag_decides(severities: list[Severity], recommendation) -> None:
    assert recommend([flag(severity) for severity in severities]) is recommendation


def test_no_recommendation_rejects_the_application() -> None:
    assert {member.name for member in Recommendation} == {
        "ACCEPT_VALUATION",
        "OFFICER_REVIEW",
        "PHYSICAL_INSPECTION",
    }


def test_missing_valuation_reports_shortage(policy) -> None:
    shortage = InsufficientComparablesError(found=2, required=5, radius_km=3.0)

    assert valuation_findings(None, shortage, policy) == [
        (ReasonCode.INSUFFICIENT_COMPARABLES, {"found": "2", "radius_km": "3.0"})
    ]


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ClaimStatus.VERIFIED, None),
        (ClaimStatus.PARTLY, ReasonCode.CONDITION_PARTLY_CONFIRMED),
        (ClaimStatus.CONTRADICTED, ReasonCode.CONDITION_CONTRADICTED),
        (ClaimStatus.INCONCLUSIVE, ReasonCode.CONDITION_INCONCLUSIVE),
        (ClaimStatus.NOT_VERIFIED, ReasonCode.CONDITION_NOT_VERIFIED),
    ],
)
def test_condition_status_maps_to_reason(status: ClaimStatus, reason) -> None:
    verification = ConditionVerification(
        declared=Condition.NEWLY_RENOVATED,
        observed=Condition.OLD_RENOVATED,
        status=status,
        valued_condition=Condition.NEWLY_RENOVATED,
        counted_photos=3,
        agreement_share=1.0,
        photos_submitted=3,
        photos_required=3,
        rules_version="test",
    )

    assert [found for found, _ in condition_findings(verification)] == ([reason] if reason else [])


def verification_with_photos(submitted: int, status: ClaimStatus) -> ConditionVerification:
    return ConditionVerification(
        declared=Condition.NEWLY_RENOVATED,
        observed=None,
        status=status,
        valued_condition=Condition.NEWLY_RENOVATED,
        counted_photos=0,
        agreement_share=None,
        photos_submitted=submitted,
        photos_required=3,
        rules_version="test",
    )


def test_fewer_photos_than_required_are_flagged_with_counts() -> None:
    findings = condition_findings(verification_with_photos(2, ClaimStatus.INCONCLUSIVE))

    assert (ReasonCode.TOO_FEW_PHOTOS, {"count": "2", "required": "3"}) in findings


def test_no_photos_message_names_the_required_count() -> None:
    findings = condition_findings(verification_with_photos(0, ClaimStatus.NOT_VERIFIED))

    assert findings == [
        (
            ReasonCode.CONDITION_NOT_VERIFIED,
            {"declared": "newly_renovated", "observed": "", "required": "3"},
        )
    ]


def test_enough_photos_raise_no_photo_count_flag() -> None:
    findings = condition_findings(verification_with_photos(3, ClaimStatus.INCONCLUSIVE))

    assert ReasonCode.TOO_FEW_PHOTOS not in [reason for reason, _ in findings]


def test_vision_not_configured_is_not_reported_as_outage() -> None:
    finding = PhotoFinding(
        sha256="a" * 64,
        width_px=1024,
        height_px=768,
        quality_issues=[],
        shows_apartment_interior=None,
        contains_people=None,
        observed_condition=None,
        vision_confidence=None,
        visible_evidence=[],
        vision_failure=VisionFailure.NOT_CONFIGURED,
        seen_in_other_applications=[],
    )

    assert photo_findings([finding], near_duplicate_pair_count=0) == []


def test_appraisal_within_range_raises_nothing() -> None:
    check = AppraisalCheck(
        appraised_value=Decimal("150000"),
        currency=Currency.USD,
        appraised_value_usd=Decimal("150000"),
        position=AppraisalPosition.WITHIN_RANGE,
        deviation_from_estimate=0.0,
    )

    assert appraisal_findings(check) == []


def test_ltv_breach_reports_ratio_limit_and_maximum() -> None:
    check = LtvCheck(
        nbg_rules_version="2026-10",
        loan_amount=Decimal("400000"),
        loan_currency=Currency.GEL,
        lending_value_usd=Decimal("150000"),
        lending_value_basis=LendingValueBasis.MODEL_ESTIMATE,
        lending_value_in_loan_currency=Decimal("389640.00"),
        ltv_limit=Decimal("0.85"),
        ltv_ratio=Decimal("1.0266"),
        is_within_limit=False,
        max_loan_amount=Decimal("331194.00"),
        gel_appreciation_stress=Decimal("0.20"),
        stressed_ltv_ratio=Decimal("1.2833"),
        is_within_limit_under_stress=False,
    )

    assert ltv_findings(check) == [
        (
            ReasonCode.LTV_ABOVE_LIMIT,
            {"ltv": "102.7", "limit": "85.0", "max_loan": "331,194.00", "currency": "GEL"},
        )
    ]


def test_severity_comes_from_policy(policy) -> None:
    flags = to_flags([(ReasonCode.CONDITION_CONTRADICTED, {})], policy)

    assert flags[0].severity is policy.flag_severity[ReasonCode.CONDITION_CONTRADICTED]
