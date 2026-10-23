from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from builders import USD_RATE
from collateral_engine.domain import Currency, ExchangeRate
from collateral_engine.money import convert_amount, round_down_to_minor_unit


def test_convert_usd_to_gel_multiplies_by_nbg_rate() -> None:
    assert convert_amount(Decimal("100000"), Currency.USD, Currency.GEL, USD_RATE) == Decimal(
        "259760.00"
    )


def test_convert_gel_to_usd_divides_by_nbg_rate() -> None:
    assert convert_amount(Decimal("259760"), Currency.GEL, Currency.USD, USD_RATE) == Decimal(
        "100000.00"
    )


def test_convert_same_currency_returns_amount_unchanged() -> None:
    amount = Decimal("1234.5678")

    assert convert_amount(amount, Currency.GEL, Currency.GEL, USD_RATE) is amount


def test_convert_rounds_to_tetri_half_even() -> None:
    rate = USD_RATE.model_copy(update={"gel_per_unit": Decimal("2.5")})

    assert convert_amount(Decimal("0.005"), Currency.USD, Currency.GEL, rate) == Decimal("0.01")


def test_round_down_never_rounds_a_limit_up() -> None:
    assert round_down_to_minor_unit(Decimal("304698.489")) == Decimal("304698.48")


def test_exchange_rate_rejects_gel_as_foreign_currency() -> None:
    with pytest.raises(ValidationError, match="foreign currency"):
        ExchangeRate(
            currency=Currency.GEL,
            gel_per_unit=Decimal("1"),
            rate_date=date(2026, 10, 22),
            source="test",
        )
