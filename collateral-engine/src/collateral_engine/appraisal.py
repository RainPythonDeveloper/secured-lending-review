"""Comparison of the licensed valuer's figure with the model range: the second opinion."""

from collateral_engine.domain import Currency, ExchangeRate, LicensedAppraisal
from collateral_engine.money import convert_amount
from collateral_engine.report import AppraisalCheck, AppraisalPosition, MarketValuation


def check_appraisal(
    appraisal: LicensedAppraisal, valuation: MarketValuation, usd_rate: ExchangeRate
) -> AppraisalCheck:
    appraised_usd = convert_amount(
        appraisal.market_value, appraisal.currency, Currency.USD, usd_rate
    )
    if appraised_usd > valuation.range_high_usd:
        position = AppraisalPosition.ABOVE_RANGE
    elif appraised_usd < valuation.range_low_usd:
        position = AppraisalPosition.BELOW_RANGE
    else:
        position = AppraisalPosition.WITHIN_RANGE
    return AppraisalCheck(
        appraised_value=appraisal.market_value,
        currency=appraisal.currency,
        appraised_value_usd=appraised_usd,
        position=position,
        deviation_from_estimate=round(float(appraised_usd / valuation.market_value_usd - 1), 4),
    )
