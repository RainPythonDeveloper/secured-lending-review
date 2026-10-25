import os

import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    os.environ["ITE_AUDIT_DB"] = str(tmp_path_factory.mktemp("a") / "audit.db")
    os.environ["ITE_API_KEY"] = "test-key"
    from api.main import app
    return TestClient(app)


def payload(bid=747):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    b = pd.read_csv(root / "data" / "borrowers.csv").set_index("borrower_id").loc[bid]
    tx = pd.read_parquet(root / "data" / "transactions.parquet")
    t = tx[tx.borrower_id == bid]
    emp = {"salaried_tbilisi": "salaried", "young_first_loan": "salaried_young", "farmer_kakheti": "farmer",
           "self_employed": "self_employed", "remittance_hh": "remittance"}[b.archetype]
    return {"application": {"borrower_id": bid, "application_date": b.application_date, "employment_type": emp,
                            "declared_income_gel": b.declared_income_gel,
                            "existing_debt_payment_declared": b.existing_debt_payment_declared,
                            "income_currency": b.income_currency, "loan_amount_gel": b.loan_amount_gel,
                            "loan_currency": b.loan_currency, "term_months": int(b.term_months),
                            "annual_rate": b.annual_rate,
                            "bureau_score": None if pd.isna(b.bureau_score) else b.bureau_score,
                            "collateral_value_gel": None if pd.isna(b.collateral_value_gel) else b.collateral_value_gel,
                            "consent_id": "OB-TEST-1"},
            "transactions": [{"tx_id": int(r.tx_id), "date": str(pd.Timestamp(r.date).date()), "amount": float(r.amount),
                              "currency": r.currency, "counterparty": r.counterparty, "description": r.description}
                             for r in t.itertuples()]}


def test_health(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["synthetic_training_data"] is True


def test_auth_required(client):
    assert client.post("/v1/assess", json=payload()).status_code == 401


def test_assess_end_to_end(client):
    r = client.post("/v1/assess", json=payload(), headers={"X-API-Key": "test-key"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["recommendation"] in {"APPROVE", "APPROVE_REDUCED", "REVIEW", "REFER"}
    assert j["offer"]["amount"] <= j["max_compliant_amount"]
    assert "features" not in j and j["consent_id"] == "OB-TEST-1"


def test_too_little_history_rejected(client):
    p = payload()
    p["transactions"] = p["transactions"][:5]
    assert client.post("/v1/assess", json=p, headers={"X-API-Key": "test-key"}).status_code == 422


def test_override_needs_reason_and_is_audited(client):
    h = {"X-API-Key": "test-key"}
    d = {"borrower_id": 747, "officer_id": "nino.b", "decision": "REJECT", "engine_recommendation": "APPROVE_REDUCED"}
    assert client.post("/v1/decisions", json=d, headers=h).status_code == 400
    d["override_reason"] = "Applicant disclosed a new large debt during the interview"
    assert client.post("/v1/decisions", json=d, headers=h).json()["recorded"] is True
    assert client.get("/v1/audit/verify", headers=h).json()["chain_intact"] is True
