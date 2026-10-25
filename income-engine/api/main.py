"""Income Truth Engine - REST API.

Stateless scoring service: every replica loads the same versioned model file, so it scales
horizontally behind a load balancer. Decisions are written to a tamper-evident audit log.

    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ite import rules  # noqa: E402
from ite.audit import AuditLog  # noqa: E402
from ite.engine import MODEL_VERSION, Engine  # noqa: E402
from ite.synth import annuity  # noqa: E402

API_KEY = os.getenv("ITE_API_KEY", "demo-key-change-me")
engine = Engine(os.getenv("ITE_MODELS_DIR", ROOT / "models"))
audit = AuditLog(os.getenv("ITE_AUDIT_DB", ROOT / "audit.db"))

app = FastAPI(title="Income Truth Engine API", version=MODEL_VERSION,
              description="Affordability, NBG-compliance and credit-risk assessment from consented account data. "
                          "Demo build trained on SYNTHETIC data only.")


def auth(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


class Application(BaseModel):
    borrower_id: int
    application_date: date
    employment_type: Literal["salaried", "salaried_young", "farmer", "self_employed", "remittance"]
    declared_income_gel: float = Field(gt=0)
    existing_debt_payment_declared: float = Field(ge=0, default=0)
    income_currency: Literal["GEL", "USD"] = "GEL"
    loan_amount_gel: float = Field(gt=0)
    loan_currency: Literal["GEL", "USD"] = "GEL"
    term_months: int = Field(ge=3, le=360)
    annual_rate: float = Field(gt=0, lt=1)
    bureau_score: Optional[float] = None
    collateral_value_gel: Optional[float] = None
    consent_id: str = Field(description="Open-banking consent reference; data use is limited to this assessment")


class Transaction(BaseModel):
    tx_id: int
    date: date
    amount: float
    currency: Literal["GEL", "USD"]
    counterparty: str
    description: str


class AssessRequest(BaseModel):
    application: Application
    transactions: list[Transaction]

    @field_validator("transactions")
    @classmethod
    def enough_history(cls, v):
        if len(v) < 20:
            raise ValueError("At least 20 transactions (about 6+ months of history) are required")
        return v


class OfficerDecision(BaseModel):
    borrower_id: int
    officer_id: str
    decision: Literal["APPROVE", "APPROVE_REDUCED", "APPROVE_SEASONAL", "REQUEST_DOCUMENTS", "REJECT"]
    amount_gel: float = 0
    engine_recommendation: str
    override_reason: Optional[str] = None
    pd_offer: Optional[float] = None
    rules_version: Optional[str] = None


def _to_frames(req: AssessRequest):
    a = req.application.model_dump()
    a["application_date"] = str(a["application_date"])
    a["thin_file"] = a["bureau_score"] is None
    a["monthly_payment_gel"] = float(annuity(a["loan_amount_gel"], a["annual_rate"], a["term_months"]))
    a["collateral_value_gel"] = a["collateral_value_gel"] if a["collateral_value_gel"] is not None else float("nan")
    a["bureau_score"] = a["bureau_score"] if a["bureau_score"] is not None else float("nan")
    tx = pd.DataFrame([t.model_dump() for t in req.transactions])
    tx["date"] = pd.to_datetime(tx["date"])
    tx["borrower_id"] = a["borrower_id"]
    return a, tx


@app.get("/health")
def health():
    ok, n = audit.verify()
    return {"status": "ok", "model_version": MODEL_VERSION, "champion": engine.risk.champion,
            "rules_version_today": rules.version_for(str(date.today()), engine.cfg)["id"],
            "audit_chain_intact": ok, "audit_records": n, "synthetic_training_data": True}


@app.get("/v1/rules")
def get_rules(as_of: date = date.today(), _=Depends(auth)):
    return rules.version_for(str(as_of), engine.cfg)


@app.post("/v1/assess")
def assess(req: AssessRequest, _=Depends(auth)):
    t0 = time.perf_counter()
    a, tx = _to_frames(req)
    try:
        out = engine.assess(a, tx)
    except Exception as e:  # never return a partial decision
        raise HTTPException(status_code=422, detail=f"Assessment failed: {e}")
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    out["consent_id"] = req.application.consent_id
    out.pop("features", None)
    return out


@app.post("/v1/decisions")
def record_decision(d: OfficerDecision, _=Depends(auth)):
    overriding = d.decision.split("_")[0] != d.engine_recommendation.split("_")[0]
    if overriding and not (d.override_reason and len(d.override_reason.strip()) >= 10):
        raise HTTPException(status_code=400, detail="Overriding the engine requires a written reason (10+ characters)")
    h = audit.append({**d.model_dump(), "override": overriding, "model_version": MODEL_VERSION})
    return {"recorded": True, "hash": h}


@app.get("/v1/audit/verify")
def verify_audit(_=Depends(auth)):
    ok, n = audit.verify()
    return {"chain_intact": ok, "records": n}
