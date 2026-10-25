"""Money conversion between GEL and USD at the NBG official rate, in Decimal only."""

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal

from collateral_engine.domain import Currency, ExchangeRate

MINOR_UNIT = Decimal("0.01")


def convert_amount(
    amount: Decimal, from_currency: Currency, to_currency: Currency, usd_rate: ExchangeRate
) -> Decimal:
    if from_currency is to_currency:
        return amount
    if usd_rate.currency is not Currency.USD:
        raise ValueError(f"expected the NBG rate for USD, got {usd_rate.currency}")
    if from_currency is Currency.USD:
        converted = amount * usd_rate.gel_per_unit
    else:
        converted = amount / usd_rate.gel_per_unit
    return converted.quantize(MINOR_UNIT, rounding=ROUND_HALF_EVEN)


def round_down_to_minor_unit(amount: Decimal) -> Decimal:
    """Limits are rounded down so that a rounded limit never exceeds the rule."""
    return amount.quantize(MINOR_UNIT, rounding=ROUND_DOWN)
