"""The NBG loan-to-value check; the limits come from the dated NBG rules file (nbg_rules.py)."""

from decimal import ROUND_DOWN, Decimal

from collateral_engine.domain import Currency, ExchangeRate, LoanRequest, SubjectProperty
from collateral_engine.money import convert_amount, round_down_to_minor_unit
from collateral_engine.nbg_rules import NbgRules, NbgRuleVersion, rule_version_in_force
from collateral_engine.policy import FxStressPolicy, ValuationPolicy
from collateral_engine.report import LendingValueBasis, LtvCheck, MarketValuation

RATIO_PRECISION = Decimal("0.0001")
WHOLE_USD = Decimal("1")


def ltv_limit_for(version: NbgRuleVersion, loan: LoanRequest) -> Decimal:
    if loan.currency is Currency.GEL:
        return version.ltv.gel
    if loan.income_from_abroad:
        return version.ltv.fx_income_from_abroad
    return version.ltv.fx


def completion_risk_factor(subject: SubjectProperty, policy: ValuationPolicy) -> Decimal | None:
    """Bank policy share of the value lent on a flat in an unfinished building."""
    if subject.off_plan is None:
        return None
    return policy.off_plan.lending_factor_by_stage[subject.off_plan.construction_stage]


def lending_value_usd(
    valuation: MarketValuation, appraised_value_usd: Decimal | None
) -> tuple[Decimal, LendingValueBasis]:
    """The more conservative of the licensed appraisal and the model."""
    if appraised_value_usd is None:
        return valuation.range_low_usd, LendingValueBasis.MODEL_RANGE_LOW
    if appraised_value_usd <= valuation.market_value_usd:
        return appraised_value_usd, LendingValueBasis.LICENSED_APPRAISAL
    return valuation.market_value_usd, LendingValueBasis.MODEL_ESTIMATE


def check_ltv(
    loan: LoanRequest,
    lending_value: tuple[Decimal, LendingValueBasis],
    usd_rate: ExchangeRate,
    rules: NbgRules,
    fx_stress: FxStressPolicy,
    completion_risk_factor: Decimal | None = None,
) -> LtvCheck:
    value_usd, basis = lending_value
    if completion_risk_factor is not None:
        value_usd = (value_usd * completion_risk_factor).quantize(WHOLE_USD, rounding=ROUND_DOWN)
    version = rule_version_in_force(rules, loan.application_date)
    limit = ltv_limit_for(version, loan)
    value_in_loan_currency = convert_amount(value_usd, Currency.USD, loan.currency, usd_rate)
    stressed_ratio = _ltv_under_lari_appreciation(loan, value_usd, usd_rate, fx_stress)
    is_stressed = stressed_ratio is not None
    return LtvCheck(
        nbg_rules_version=version.id,
        loan_amount=loan.amount,
        loan_currency=loan.currency,
        lending_value_usd=value_usd,
        lending_value_basis=basis,
        completion_risk_factor=completion_risk_factor,
        lending_value_in_loan_currency=value_in_loan_currency,
        ltv_limit=limit,
        ltv_ratio=(loan.amount / value_in_loan_currency).quantize(RATIO_PRECISION),
        is_within_limit=loan.amount <= value_in_loan_currency * limit,
        max_loan_amount=round_down_to_minor_unit(value_in_loan_currency * limit),
        gel_appreciation_stress=fx_stress.gel_appreciation if is_stressed else None,
        stressed_ltv_ratio=stressed_ratio.quantize(RATIO_PRECISION) if is_stressed else None,
        is_within_limit_under_stress=stressed_ratio <= limit if is_stressed else None,
    )


def _ltv_under_lari_appreciation(
    loan: LoanRequest, value_usd: Decimal, usd_rate: ExchangeRate, fx_stress: FxStressPolicy
) -> Decimal | None:
    """A GEL loan on a USD-priced flat: if the lari strengthens, the collateral shrinks in GEL."""
    if loan.currency is not Currency.GEL:
        return None
    stressed_value_gel = value_usd * usd_rate.gel_per_unit * (1 - fx_stress.gel_appreciation)
    return loan.amount / stressed_value_gel
