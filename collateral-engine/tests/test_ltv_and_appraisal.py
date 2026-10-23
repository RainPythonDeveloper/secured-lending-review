from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from builders import USD_RATE, VALUATION_DATE
from collateral_engine.appraisal import check_appraisal
from collateral_engine.domain import Currency, LicensedAppraisal, LoanRequest
from collateral_engine.ltv import check_ltv, lending_value_usd, ltv_limit_for
from collateral_engine.nbg_rules import (
    NbgRules,
    NoRuleInForceError,
    ValuationLimits,
    load_nbg_rules,
    rule_version_in_force,
)
from collateral_engine.policy import FxStressPolicy
from collateral_engine.report import (
    AdjustmentTier,
    AppraisalPosition,
    LendingValueBasis,
    MarketValuation,
)

FX_STRESS = FxStressPolicy(gel_appreciation=Decimal("0.20"))
VALUATION_LIMITS = ValuationLimits(
    min_comparables=3,
    max_single_adjustment=0.15,
    max_gross_adjustment=0.25,
    max_gross_adjustment_justified=0.35,
)


def valuation(
    estimate: str = "150000", low: str = "130000", high: str = "175000"
) -> MarketValuation:
    return MarketValuation(
        valued_condition="newly_renovated",
        price_per_m2_usd=Decimal("1800"),
        market_value_usd=Decimal(estimate),
        range_low_usd=Decimal(low),
        range_high_usd=Decimal(high),
        range_coverage=0.8,
        hedonic_value_usd=Decimal(estimate),
        model_disagreement=0.0,
        search_radius_km=1.5,
        was_radius_widened=False,
        adjustment_tier=AdjustmentTier.WITHIN_LIMITS,
        valuation_limits=VALUATION_LIMITS,
        comparables=[],
    )


def loan(
    amount: str,
    currency: Currency = Currency.GEL,
    income_from_abroad: bool = False,
    application_date: date = VALUATION_DATE,
) -> LoanRequest:
    return LoanRequest(
        amount=Decimal(amount),
        currency=currency,
        application_date=application_date,
        income_from_abroad=income_from_abroad,
    )


@pytest.mark.parametrize(
    ("currency", "income_from_abroad", "limit"),
    [
        (Currency.GEL, False, Decimal("0.90")),
        (Currency.GEL, True, Decimal("0.90")),
        (Currency.USD, False, Decimal("0.70")),
        (Currency.USD, True, Decimal("0.80")),
    ],
)
def test_repository_rules_set_current_nbg_ltv_limits(
    nbg_rules: NbgRules, currency: Currency, income_from_abroad: bool, limit: Decimal
) -> None:
    version = rule_version_in_force(nbg_rules, VALUATION_DATE)

    assert ltv_limit_for(version, loan("1", currency, income_from_abroad)) == limit


def test_gel_ltv_was_85_percent_before_the_2025_easing(nbg_rules: NbgRules) -> None:
    version = rule_version_in_force(nbg_rules, date(2025, 2, 25))

    assert ltv_limit_for(version, loan("1", application_date=date(2025, 2, 25))) == Decimal("0.85")


def test_repository_rules_carry_84_04_valuation_limits(nbg_rules: NbgRules) -> None:
    limits = rule_version_in_force(nbg_rules, VALUATION_DATE).valuation

    assert (
        limits.min_comparables,
        limits.max_single_adjustment,
        limits.max_gross_adjustment,
        limits.max_gross_adjustment_justified,
    ) == (3, 0.15, 0.25, 0.35)


def test_rule_version_is_the_one_in_force_on_application_date(tmp_path: Path) -> None:
    path = tmp_path / "nbg_rules.yaml"
    path.write_text(
        "valuation: &v {min_comparables: 3, max_single_adjustment: 0.15,"
        " max_gross_adjustment: 0.25, max_gross_adjustment_justified: 0.35}\n"
        "versions:\n"
        "  - {id: old, effective_from: 2020-01-01,"
        " ltv: {gel: 0.85, fx: 0.70, fx_income_from_abroad: 0.70}, valuation: *v}\n"
        "  - {id: new, effective_from: 2027-02-01,"
        " ltv: {gel: 0.80, fx: 0.65, fx_income_from_abroad: 0.75}, valuation: *v}\n"
    )
    rules = load_nbg_rules(path)

    assert rule_version_in_force(rules, date(2027, 1, 31)).id == "old"
    assert rule_version_in_force(rules, date(2027, 2, 1)).id == "new"


def test_date_before_any_rule_is_refused(nbg_rules: NbgRules) -> None:
    with pytest.raises(NoRuleInForceError):
        rule_version_in_force(nbg_rules, date(2000, 1, 1))


def test_lending_value_without_appraisal_is_range_low() -> None:
    assert lending_value_usd(valuation(), None) == (
        Decimal("130000"),
        LendingValueBasis.MODEL_RANGE_LOW,
    )


@pytest.mark.parametrize(
    ("appraised", "expected"),
    [
        ("140000", (Decimal("140000"), LendingValueBasis.LICENSED_APPRAISAL)),
        ("190000", (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE)),
    ],
)
def test_lending_value_is_lower_of_appraisal_and_estimate(appraised: str, expected: tuple) -> None:
    assert lending_value_usd(valuation(), Decimal(appraised)) == expected


def test_gel_loan_ltv_uses_nbg_rate_and_gel_limit(nbg_rules: NbgRules) -> None:
    check = check_ltv(
        loan("300000"),
        (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE),
        USD_RATE,
        nbg_rules,
        FX_STRESS,
    )

    assert check.lending_value_in_loan_currency == Decimal("389640.00")
    assert check.ltv_ratio == Decimal("0.7699")
    assert check.max_loan_amount == Decimal("350676.00")
    assert check.is_within_limit


def test_loan_above_limit_is_flagged_with_max_amount(nbg_rules: NbgRules) -> None:
    check = check_ltv(
        loan("360000"),
        (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE),
        USD_RATE,
        nbg_rules,
        FX_STRESS,
    )

    assert not check.is_within_limit
    assert check.max_loan_amount == Decimal("350676.00")


def test_stronger_lari_raises_ltv_of_gel_loan(nbg_rules: NbgRules) -> None:
    check = check_ltv(
        loan("300000"),
        (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE),
        USD_RATE,
        nbg_rules,
        FX_STRESS,
    )

    assert check.stressed_ltv_ratio == Decimal("0.9624")
    assert check.is_within_limit_under_stress is False


def test_usd_loan_uses_fx_limit_and_has_no_lari_stress(nbg_rules: NbgRules) -> None:
    check = check_ltv(
        loan("100000", Currency.USD),
        (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE),
        USD_RATE,
        nbg_rules,
        FX_STRESS,
    )

    assert (check.ltv_limit, check.max_loan_amount) == (Decimal("0.70"), Decimal("105000.00"))
    assert check.stressed_ltv_ratio is None


def test_fx_mortgage_with_income_from_abroad_gets_higher_limit(nbg_rules: NbgRules) -> None:
    check = check_ltv(
        loan("115000", Currency.USD, income_from_abroad=True),
        (Decimal("150000"), LendingValueBasis.MODEL_ESTIMATE),
        USD_RATE,
        nbg_rules,
        FX_STRESS,
    )

    assert (check.ltv_limit, check.max_loan_amount) == (Decimal("0.80"), Decimal("120000.00"))
    assert check.is_within_limit


@pytest.mark.parametrize(
    ("value", "currency", "position"),
    [
        ("160000", Currency.USD, AppraisalPosition.WITHIN_RANGE),
        ("200000", Currency.USD, AppraisalPosition.ABOVE_RANGE),
        ("100000", Currency.USD, AppraisalPosition.BELOW_RANGE),
        ("519520", Currency.GEL, AppraisalPosition.ABOVE_RANGE),
    ],
)
def test_appraisal_position_against_model_range(
    value: str, currency: Currency, position: AppraisalPosition
) -> None:
    appraisal = LicensedAppraisal(
        market_value=Decimal(value), currency=currency, appraisal_date=VALUATION_DATE
    )

    assert check_appraisal(appraisal, valuation(), USD_RATE).position is position


def test_appraisal_deviation_is_relative_to_estimate() -> None:
    appraisal = LicensedAppraisal(
        market_value=Decimal("180000"), currency=Currency.USD, appraisal_date=VALUATION_DATE
    )

    assert check_appraisal(appraisal, valuation(), USD_RATE).deviation_from_estimate == 0.2
