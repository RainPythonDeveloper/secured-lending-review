import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from collateral_engine.domain import Currency
from collateral_engine.nbg_rates import (
    NBG_RATE_SOURCE,
    NbgRatesClient,
    OfficialRateUnavailableError,
    parse_official_rate,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nbg_rates"
RATES_URL = "https://nbg.example/rates"


def load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def client_answering(handler: httpx.MockTransport) -> NbgRatesClient:
    return NbgRatesClient(httpx.Client(transport=handler), RATES_URL, timeout_s=1.0)


def test_parse_reads_usd_rate_as_exact_decimal() -> None:
    rate = parse_official_rate(
        load_fixture("usd.2026-10-20.json"), Currency.USD, date(2026, 10, 20)
    )

    assert (rate.gel_per_unit, rate.rate_date, rate.source) == (
        Decimal("2.5979"),
        date(2026, 10, 20),
        NBG_RATE_SOURCE,
    )


def test_parse_picks_requested_currency_among_several() -> None:
    rate = parse_official_rate(
        load_fixture("eur-usd.2026-10-20.json"), Currency.USD, date(2026, 10, 20)
    )

    assert rate.gel_per_unit == Decimal("2.5979")


def test_parse_divides_by_quoted_quantity() -> None:
    payload = load_fixture("usd.2026-10-20.json")
    payload[0]["currencies"][0].update(quantity=100, rateFormated="259.79")

    rate = parse_official_rate(payload, Currency.USD, date(2026, 10, 20))

    assert rate.gel_per_unit == Decimal("2.5979")


def test_parse_rejects_latest_rate_given_for_unpublished_date() -> None:
    with pytest.raises(OfficialRateUnavailableError, match="2026-10-23"):
        parse_official_rate(
            load_fixture("usd.requested-2027-05-01.json"), Currency.USD, date(2027, 5, 1)
        )


def test_parse_rejects_empty_answer() -> None:
    with pytest.raises(OfficialRateUnavailableError, match="no rates"):
        parse_official_rate(
            load_fixture("unknown-currency.2026-10-20.json"), Currency.USD, date(2026, 10, 20)
        )


def test_parse_rejects_answer_without_requested_currency() -> None:
    payload = load_fixture("eur-usd.2026-10-20.json")
    payload[0]["currencies"] = payload[0]["currencies"][:1]

    with pytest.raises(OfficialRateUnavailableError, match="no USD rate"):
        parse_official_rate(payload, Currency.USD, date(2026, 10, 20))


@pytest.mark.parametrize("payload", [{"unexpected": True}, [{"date": "not a date"}]])
def test_parse_rejects_unexpected_payload(payload: object) -> None:
    with pytest.raises(OfficialRateUnavailableError, match="unexpected payload"):
        parse_official_rate(payload, Currency.USD, date(2026, 10, 20))


def test_fetch_sends_currency_and_date_and_parses_answer() -> None:
    seen_params = {}

    def answer(request: httpx.Request) -> httpx.Response:
        seen_params.update(request.url.params)
        return httpx.Response(200, json=load_fixture("usd.2026-10-20.json"))

    rate = client_answering(httpx.MockTransport(answer)).fetch_rate(
        Currency.USD, date(2026, 10, 20)
    )

    assert (seen_params, rate.gel_per_unit) == (
        {"currencies": "USD", "date": "2026-10-20"},
        Decimal("2.5979"),
    )


def test_fetch_reports_server_error_as_unavailable() -> None:
    client = client_answering(httpx.MockTransport(lambda _: httpx.Response(503)))

    with pytest.raises(OfficialRateUnavailableError, match="request failed"):
        client.fetch_rate(Currency.USD, date(2026, 10, 20))


def test_fetch_reports_timeout_as_unavailable() -> None:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(OfficialRateUnavailableError, match="did not answer"):
        client_answering(httpx.MockTransport(time_out)).fetch_rate(Currency.USD, date(2026, 10, 20))


def test_fetch_reports_invalid_json_as_unavailable() -> None:
    client = client_answering(httpx.MockTransport(lambda _: httpx.Response(200, text="<html>")))

    with pytest.raises(OfficialRateUnavailableError, match="invalid JSON"):
        client.fetch_rate(Currency.USD, date(2026, 10, 20))
