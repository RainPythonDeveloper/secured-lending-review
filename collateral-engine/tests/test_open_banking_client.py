"""The Open Banking gateway client: the consent journey and reading accounts, with HTTP mocked."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from collateral_engine.lending.bank_data import load_bank_snapshot
from collateral_engine.lending.customer import DataSource
from collateral_engine.lending.open_banking import OpenBankingClient, OpenBankingError
from collateral_engine.settings import DEFAULT_BANK_DATASET_PATH

FIXTURES = Path(__file__).parent / "fixtures" / "open_banking"
GATEWAY_URL = "http://gateway.test"
CONSENT_ID = "8e3f2a51-6c1b-4f0e-9a4d-2b7c5e1d9f30"
PERIOD = (date(2026, 4, 20), date(2026, 10, 20))


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def gateway(requests: list[httpx.Request]) -> httpx.MockTransport:
    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/v1/consents":
            body = fixture("consent_created.json")
            return httpx.Response(201, json=body, headers={"X-Data-Source": "organizer-dataset"})
        if path.endswith("/status"):
            return httpx.Response(200, json={"consentStatus": "valid"})
        if path == "/v1/accounts":
            return httpx.Response(200, json=fixture("accounts.json"))
        return httpx.Response(200, json=fixture("transactions.json"))

    return httpx.MockTransport(answer)


def client_with(transport: httpx.MockTransport) -> OpenBankingClient:
    return OpenBankingClient(httpx.Client(transport=transport), GATEWAY_URL, timeout_s=5.0)


@pytest.fixture(scope="module")
def customer():
    return load_bank_snapshot(DEFAULT_BANK_DATASET_PATH).customer("CUS-001")


def test_consent_names_the_dataset_customer_and_the_bank_page() -> None:
    requests: list[httpx.Request] = []

    consent = client_with(gateway(requests)).start_consent("CUS-001", date(2026, 10, 22))

    assert requests[0].headers["PSU-ID"] == "CUS-001"
    assert consent.authorisation_url.startswith("https://tbc-bank-mock-open-banking-api")
    assert consent.data_source == "organizer-dataset"


def test_every_request_carries_its_own_request_id() -> None:
    requests: list[httpx.Request] = []
    client = client_with(gateway(requests))

    client.start_consent("CUS-001", date(2026, 10, 22))
    client.is_consent_valid(CONSENT_ID)

    request_ids = {request.headers["X-Request-ID"] for request in requests}
    assert len(request_ids) == 2


def test_valid_consent_is_recognised() -> None:
    assert client_with(gateway([])).is_consent_valid(CONSENT_ID)


def test_customer_file_maps_berlin_group_fields(customer) -> None:
    customer_file = client_with(gateway([])).customer_file(CONSENT_ID, customer, *PERIOD)

    salary = customer_file.transactions[0]
    assert customer_file.source is DataSource.OPEN_BANKING
    assert (salary.category, salary.counterparty, str(salary.amount)) == (
        "salary",
        "Rioni Technology (synthetic)",
        "2150.00",
    )


def test_customer_file_reads_the_consented_account(customer) -> None:
    requests: list[httpx.Request] = []

    client_with(gateway(requests)).customer_file(CONSENT_ID, customer, *PERIOD)

    assert all(request.headers["Consent-ID"] == CONSENT_ID for request in requests)


@pytest.mark.parametrize("status", [401, 502])
def test_gateway_error_is_reported(status: int) -> None:
    failing = httpx.MockTransport(
        lambda _: httpx.Response(status, json={"detail": "Injected synthetic failure"})
    )

    with pytest.raises(OpenBankingError, match=str(status)):
        client_with(failing).is_consent_valid(CONSENT_ID)


def test_unreachable_gateway_is_reported() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(OpenBankingError, match="ConnectError"):
        client_with(httpx.MockTransport(refuse)).is_consent_valid(CONSENT_ID)


def test_unexpected_body_is_reported() -> None:
    odd = httpx.MockTransport(lambda _: httpx.Response(200, json={"unexpected": True}))

    with pytest.raises(OpenBankingError, match="unexpected body"):
        client_with(odd).is_consent_valid(CONSENT_ID)
