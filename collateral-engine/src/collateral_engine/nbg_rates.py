"""Official exchange rates of the National Bank of Georgia (nbg.gov.ge public API).

For a date NBG has not published yet, the API answers with the latest published rate instead of
an error, so the date of every answer is checked against the requested one.
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from collateral_engine.domain import Currency, ExchangeRate

logger = logging.getLogger(__name__)

NBG_RATE_SOURCE = "NBG official exchange rate"


class OfficialRateUnavailableError(Exception):
    """NBG did not provide the rate for the requested currency and date."""


class NbgCurrencyRate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    code: str
    quantity: int = Field(gt=0)
    # Field name exactly as NBG publishes it.
    rate_formated: str = Field(alias="rateFormated")


class NbgRatesDay(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: datetime
    currencies: list[NbgCurrencyRate]


_RATES_PAYLOAD = TypeAdapter(list[NbgRatesDay])


def parse_official_rate(payload: object, currency: Currency, rate_date: date) -> ExchangeRate:
    try:
        days = _RATES_PAYLOAD.validate_python(payload)
    except ValidationError as error:
        raise OfficialRateUnavailableError("NBG answered with an unexpected payload") from error
    day = _day_for(days, rate_date)
    currency_rate = _rate_for(day, currency)
    try:
        rate = Decimal(currency_rate.rate_formated)
    except InvalidOperation as error:
        raise OfficialRateUnavailableError(
            f"NBG rate '{currency_rate.rate_formated}' is not a number"
        ) from error
    return ExchangeRate(
        currency=currency,
        gel_per_unit=rate / currency_rate.quantity,
        rate_date=rate_date,
        source=NBG_RATE_SOURCE,
    )


def _day_for(days: list[NbgRatesDay], rate_date: date) -> NbgRatesDay:
    if not days:
        raise OfficialRateUnavailableError(f"NBG returned no rates for {rate_date}")
    day = days[0]
    if day.date.date() != rate_date:
        raise OfficialRateUnavailableError(
            f"NBG has no rate for {rate_date} yet; it answered with {day.date.date()}"
        )
    return day


def _rate_for(day: NbgRatesDay, currency: Currency) -> NbgCurrencyRate:
    for currency_rate in day.currencies:
        if currency_rate.code == currency.value:
            return currency_rate
    raise OfficialRateUnavailableError(f"NBG returned no {currency} rate for {day.date.date()}")


class NbgRatesClient:
    def __init__(self, http_client: httpx.Client, base_url: str, timeout_s: float) -> None:
        self._http_client = http_client
        self._base_url = base_url
        self._timeout_s = timeout_s

    def fetch_rate(self, currency: Currency, rate_date: date) -> ExchangeRate:
        params = {"currencies": currency.value, "date": rate_date.isoformat()}
        try:
            response = self._http_client.get(self._base_url, params=params, timeout=self._timeout_s)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise OfficialRateUnavailableError(
                f"NBG rate API did not answer within {self._timeout_s} s"
            ) from error
        except httpx.HTTPError as error:
            raise OfficialRateUnavailableError(f"NBG rate API request failed: {error}") from error
        except ValueError as error:
            raise OfficialRateUnavailableError("NBG rate API returned invalid JSON") from error
        logger.info("Fetched NBG %s rate for %s", currency, rate_date)
        return parse_official_rate(payload, currency, rate_date)
