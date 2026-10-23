import json
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from builders import USD_RATE, make_appraisal, make_house, make_request, scene_photo
from collateral_engine.api import PROBLEM_JSON, create_app
from collateral_engine.domain import Currency
from collateral_engine.nbg_rates import OfficialRateUnavailableError


class StubRatesClient:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def fetch_rate(self, currency: Currency, rate_date: date):
        if self._error is not None:
            raise self._error
        return USD_RATE.model_copy(update={"rate_date": rate_date})


@pytest.fixture
def client(make_engine) -> TestClient:
    return TestClient(create_app(make_engine(), StubRatesClient()))


def post_valuation(client: TestClient, request_json: str, photos: list[bytes] = ()):
    files = [
        ("photos", (f"room-{index}.jpg", content, "image/jpeg"))
        for index, content in enumerate(photos)
    ]
    return client.post("/v1/valuations", data={"request": request_json}, files=files or None)


def test_health_reports_model_version_and_market_size(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["comparable_sales"] > 0


def test_districts_reference_lists_ten_districts_in_georgian(client: TestClient) -> None:
    districts = client.get("/v1/reference/districts").json()

    assert len(districts) == 10
    assert {"vake", "ვაკე"} <= {value for district in districts for value in district.values()}


def test_create_valuation_returns_report_with_ltv(client: TestClient) -> None:
    response = post_valuation(client, make_request().model_dump_json(), [scene_photo(seed=1)])

    body = response.json()
    assert response.status_code == 201
    assert body["ltv"]["ltv_limit"] == "0.9"
    assert len(body["photos"]) == 1


def test_create_valuation_values_a_house_with_land(client: TestClient) -> None:
    response = post_valuation(client, make_request(subject=make_house()).model_dump_json())

    body = response.json()
    assert response.status_code == 201
    assert body["subject"]["property_kind"] == "house"
    assert body["valuation"]["comparables"][0]["land_area_m2"] is not None


def test_house_without_land_area_is_rejected_as_problem_json(client: TestClient) -> None:
    request = json.loads(make_request(subject=make_house()).model_dump_json())
    request["subject"]["land_area_m2"] = None

    response = post_valuation(client, json.dumps(request))

    assert response.status_code == 400
    assert response.headers["content-type"].startswith(PROBLEM_JSON)


def test_create_valuation_accepts_request_without_photos(client: TestClient) -> None:
    response = post_valuation(client, make_request().model_dump_json())

    assert response.status_code == 201
    assert response.json()["condition"]["status"] == "NOT_VERIFIED"


def test_invalid_request_json_is_problem_json(client: TestClient) -> None:
    response = post_valuation(client, '{"application_id": "X"}')

    assert response.status_code == 400
    assert response.headers["content-type"] == PROBLEM_JSON
    assert response.json()["code"] == "FORMAT_ERROR"


def test_request_outside_tbilisi_is_refused(client: TestClient) -> None:
    request = make_request().model_dump(mode="json")
    request["subject"]["cadastral_code"] = "02.05.11.555.001.01.501"

    response = post_valuation(client, json.dumps(request))

    assert response.status_code == 400
    assert "Tbilisi only" in response.json()["detail"]


def test_rate_must_match_valuation_date(client: TestClient) -> None:
    request = make_request().model_dump(mode="json")
    request["usd_rate"]["rate_date"] = "2026-10-21"

    response = post_valuation(client, json.dumps(request))

    assert response.status_code == 400
    assert "valuation date" in response.json()["detail"]


def test_decision_against_recommendation_without_reason_is_refused(client: TestClient) -> None:
    valuation = post_valuation(client, make_request().model_dump_json()).json()

    response = client.post(
        f"/v1/valuations/{valuation['valuation_id']}/decision",
        json={"officer_id": "officer-7", "decision": "ACCEPT_VALUATION"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REASON_REQUIRED"


def test_decision_with_reason_is_recorded_and_chain_stays_intact(client: TestClient) -> None:
    request = make_request(appraisal=make_appraisal("150000"))
    valuation = post_valuation(client, request.model_dump_json()).json()

    response = client.post(
        f"/v1/valuations/{valuation['valuation_id']}/decision",
        json={
            "officer_id": "officer-7",
            "decision": "ACCEPT_VALUATION",
            "reason": "Valuer's photos reviewed in the branch",
        },
    )

    assert response.status_code == 201
    assert client.get("/v1/audit/verify").json() == {"is_intact": True, "records_checked": 2}


def test_decision_on_unknown_valuation_is_not_found(client: TestClient) -> None:
    response = client.post(
        "/v1/valuations/unknown/decision",
        json={"officer_id": "officer-7", "decision": "PHYSICAL_INSPECTION"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_UNKNOWN"


def test_usd_rate_comes_from_nbg_client(client: TestClient) -> None:
    response = client.get("/v1/exchange-rates/usd", params={"rate_date": "2026-10-20"})

    assert response.json() == {
        "currency": "USD",
        "gel_per_unit": str(Decimal("2.5976")),
        "rate_date": "2026-10-20",
        "source": "NBG official exchange rate",
    }


def test_unavailable_nbg_rate_is_bad_gateway(make_engine) -> None:
    failing = StubRatesClient(OfficialRateUnavailableError("NBG has no rate for 2027-05-01 yet"))
    client = TestClient(create_app(make_engine(), failing))

    response = client.get("/v1/exchange-rates/usd", params={"rate_date": "2027-05-01"})

    assert response.status_code == 502
    assert response.json()["code"] == "RATE_UNAVAILABLE"
