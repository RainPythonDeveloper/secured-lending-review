"""LTV of a vehicle loan against the bank's policy; NBG sets no LTV limit for vehicles."""

from decimal import Decimal

from collateral_engine.domain import Currency, ExchangeRate
from collateral_engine.ltv import RATIO_PRECISION
from collateral_engine.money import convert_amount, round_down_to_minor_unit
from collateral_engine.vehicles.domain import VehicleLoanRequest
from collateral_engine.vehicles.policy import VehiclePolicy
from collateral_engine.vehicles.report import VehicleLtvCheck, VehicleMarketValuation


def check_vehicle_ltv(
    loan: VehicleLoanRequest,
    valuation: VehicleMarketValuation,
    usd_rate: ExchangeRate,
    policy: VehiclePolicy,
) -> VehicleLtvCheck:
    value_usd = valuation.range_low_usd
    limit = policy.lending.max_ltv
    value_in_loan_currency = convert_amount(value_usd, Currency.USD, loan.currency, usd_rate)
    stressed_ratio = _ltv_under_lari_appreciation(loan, value_usd, usd_rate, policy)
    is_stressed = stressed_ratio is not None
    return VehicleLtvCheck(
        policy_version=policy.version,
        loan_amount=loan.amount,
        loan_currency=loan.currency,
        lending_value_usd=value_usd,
        lending_value_in_loan_currency=value_in_loan_currency,
        ltv_limit=limit,
        ltv_ratio=(loan.amount / value_in_loan_currency).quantize(RATIO_PRECISION),
        is_within_limit=loan.amount <= value_in_loan_currency * limit,
        max_loan_amount=round_down_to_minor_unit(value_in_loan_currency * limit),
        gel_appreciation_stress=policy.fx_stress.gel_appreciation if is_stressed else None,
        stressed_ltv_ratio=stressed_ratio.quantize(RATIO_PRECISION) if is_stressed else None,
        is_within_limit_under_stress=stressed_ratio <= limit if is_stressed else None,
    )


def _ltv_under_lari_appreciation(
    loan: VehicleLoanRequest, value_usd: Decimal, usd_rate: ExchangeRate, policy: VehiclePolicy
) -> Decimal | None:
    """A GEL loan on a USD-priced vehicle: a stronger lari shrinks the collateral in GEL."""
    if loan.currency is not Currency.GEL:
        return None
    stress = policy.fx_stress.gel_appreciation
    return loan.amount / (value_usd * usd_rate.gel_per_unit * (1 - stress))
