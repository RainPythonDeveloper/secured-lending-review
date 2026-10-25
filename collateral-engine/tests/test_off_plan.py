from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from builders import make_request, make_subject
from collateral_engine.domain import BuildingStatus, Condition, ConstructionStage, OffPlanDetails
from collateral_engine.findings import off_plan_findings, to_flags
from collateral_engine.flags import ReasonCode
from collateral_engine.i18n import Language, reason_text
from collateral_engine.ltv import completion_risk_factor

VALUATION_DATE = date(2026, 10, 22)


def off_plan(**changes: object) -> OffPlanDetails:
    base = {
        "developer_name": "Invented Developer LLC",
        "construction_stage": ConstructionStage.STRUCTURAL_FRAME,
        "expected_completion_date": date(2027, 12, 31),
        "purchase_agreement_registered": True,
    }
    return OffPlanDetails(**{**base, **changes})


def off_plan_subject(**changes: object):
    return make_subject(
        building_status=BuildingStatus.UNDER_CONSTRUCTION,
        declared_condition=Condition.WHITE_FRAME,
        off_plan=off_plan(**changes),
    )


def codes(subject, policy) -> list[ReasonCode]:
    return [code for code, _ in off_plan_findings(subject, VALUATION_DATE, policy)]


def test_building_under_construction_needs_off_plan_details() -> None:
    with pytest.raises(ValidationError, match="off_plan"):
        make_subject(building_status=BuildingStatus.UNDER_CONSTRUCTION)


def test_completed_building_must_not_carry_off_plan_details() -> None:
    with pytest.raises(ValidationError, match="off_plan"):
        make_subject(off_plan=off_plan())


@pytest.mark.parametrize("stage", list(ConstructionStage))
def test_every_stage_has_a_lending_factor(policy, stage: ConstructionStage) -> None:
    factor = completion_risk_factor(off_plan_subject(construction_stage=stage), policy)

    assert Decimal("0") < factor <= Decimal("1")


def test_earlier_stage_lends_less(policy) -> None:
    foundation = completion_risk_factor(
        off_plan_subject(construction_stage=ConstructionStage.FOUNDATION), policy
    )
    finishing = completion_risk_factor(
        off_plan_subject(construction_stage=ConstructionStage.FINISHING), policy
    )

    assert foundation < finishing


def test_completed_flat_has_no_completion_discount(policy) -> None:
    assert completion_risk_factor(make_subject(), policy) is None


def test_stage_discount_is_always_explained(policy) -> None:
    assert ReasonCode.OFF_PLAN_STAGE_DISCOUNT in codes(off_plan_subject(), policy)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"expected_completion_date": date(2026, 9, 30)}, ReasonCode.OFF_PLAN_COMPLETION_OVERDUE),
        ({"expected_completion_date": date(2029, 6, 30)}, ReasonCode.OFF_PLAN_LONG_COMPLETION),
        ({"purchase_agreement_registered": False}, ReasonCode.OFF_PLAN_AGREEMENT_NOT_REGISTERED),
    ],
)
def test_off_plan_risk_flags(policy, changes: dict, code: ReasonCode) -> None:
    assert code in codes(off_plan_subject(**changes), policy)


def test_engine_lowers_lending_value_for_unfinished_building(make_engine, policy) -> None:
    engine = make_engine()
    subject = off_plan_subject()

    report = engine.assess(make_request(subject=subject), [])

    factor = policy.off_plan.lending_factor_by_stage[ConstructionStage.STRUCTURAL_FRAME]
    assert report.ltv.completion_risk_factor == factor
    assert report.ltv.lending_value_usd <= report.valuation.range_low_usd * factor


def test_stage_name_is_translated_in_reason(policy) -> None:
    specs = off_plan_findings(off_plan_subject(), VALUATION_DATE, policy)
    flag = to_flags(specs, policy)[0]

    assert "კონსტრუქციული კარკასი" in reason_text(flag, Language.GEORGIAN)
