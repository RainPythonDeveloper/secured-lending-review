import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ite import features, synth
from ite.engine import Engine
from ite.models import RISK_FEATURES, INCOME_FEATURES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def eng():
    return Engine(ROOT / "models")


@pytest.fixture(scope="module")
def data():
    bor = pd.read_csv(ROOT / "data" / "borrowers.csv")
    tx = pd.read_parquet(ROOT / "data" / "transactions.parquet")
    return bor, tx


def test_generator_is_reproducible():
    a, b = synth.generate(200, seed=7), synth.generate(200, seed=7)
    pd.testing.assert_frame_equal(a.borrowers, b.borrowers)
    assert len(a.transactions) == len(b.transactions)


def test_no_ground_truth_leaks_into_models():
    for f in INCOME_FEATURES + RISK_FEATURES:
        assert not f.startswith("TRUE_") and f not in ("category_true", "is_round_trip")


def test_protected_attributes_not_model_inputs():
    for f in INCOME_FEATURES + RISK_FEATURES:
        assert f not in ("gender", "age", "region")


def test_single_matches_batch(eng, data):
    bor, tx = data
    hidden = [c for c in bor.columns if c.startswith("TRUE_")]
    dec = pd.read_parquet(ROOT / "reports" / "decisions_test.parquet").set_index("borrower_id")
    for bid in dec.index[:5]:
        app = bor[bor.borrower_id == bid].drop(columns=hidden).iloc[0].to_dict()
        r = eng.assess(app, tx[tx.borrower_id == bid].drop(columns=["category_true", "is_round_trip"]))
        assert r["recommendation"] == dec.at[bid, "recommendation"]
        assert r["pd_offer"] == pytest.approx(dec.at[bid, "pd_offer"], abs=1e-3)


def test_offers_never_break_pti(eng):
    dec = pd.read_parquet(ROOT / "reports" / "decisions_test.parquet")
    o = dec[dec.offer_amount > 0]
    assert (o.offer_amount <= o.max_compliant_amount + 1e-6).all()
    pti = (o.existing_debt + o.offer_payment) / o.inc_q25
    assert (pti <= o.pti_limit + 1e-3).all()          # tolerance: reported income is rounded to 1 GEL


def test_engine_never_recommends_rejection():
    # Only the loan officer may refuse; the engine refers instead.
    dec = pd.read_parquet(ROOT / "reports" / "decisions_test.parquet")
    assert set(dec.recommendation) <= {"APPROVE", "APPROVE_REDUCED", "REVIEW", "REFER"}


def test_more_debt_never_lowers_risk(eng, data):
    bor, tx = data
    bid = int(bor[bor.cohort == "B"].borrower_id.iloc[3])
    app = bor[bor.borrower_id == bid].iloc[0].to_dict()
    t = tx[tx.borrower_id == bid].drop(columns=["category_true", "is_round_trip"])
    lo = eng.assess({**app, "loan_amount_gel": 2000, "monthly_payment_gel": float(synth.annuity(2000, app["annual_rate"], app["term_months"]))}, t)
    hi = eng.assess({**app, "loan_amount_gel": 20000, "monthly_payment_gel": float(synth.annuity(20000, app["annual_rate"], app["term_months"]))}, t)
    assert hi["pd_requested"] >= lo["pd_requested"]


def test_reasons_are_bilingual_and_consistent(eng, data):
    bor, tx = data
    bid = 747
    app = bor[bor.borrower_id == bid].iloc[0].to_dict()
    r = eng.assess(app, tx[tx.borrower_id == bid].drop(columns=["category_true", "is_round_trip"]))
    assert r["reasons"] and all(x["ka"] and x["en"] for x in r["reasons"])
    assert "ეროვნული ბანკის" in r["letter_ka"] and "National Bank of Georgia" in r["letter_en"]


def test_metrics_meet_release_gates():
    M = json.loads((ROOT / "reports" / "metrics.json").read_text())
    assert M["risk"]["engine"]["auc"] > M["risk"]["traditional_bureau"]["auc"]
    assert M["income"]["mdape_engine_p50"] < M["income"]["mdape_declared"]
    assert 0.75 <= M["income"]["band_coverage_p10_p90"] <= 0.85
    assert all(v["pass"] for v in M["risk"]["sign_checks"].values())
    assert M["sanity_counterfactual_max_error"] < 1e-3
