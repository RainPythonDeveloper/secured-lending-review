"""NBG responsible-lending rules (PTI / LTV) from a versioned, dated config file.

The model can never recommend an amount that breaks these rules: the maximum compliant
amount is computed here and caps every offer.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "nbg_rules.yaml"


@lru_cache(maxsize=8)
def load(path: str | Path = DEFAULT_PATH) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    cfg["versions"] = sorted(cfg["versions"], key=lambda v: v["effective_from"])
    return cfg


def version_for(as_of: str, cfg: dict | None = None) -> dict:
    cfg = cfg or load()
    valid = [v for v in cfg["versions"] if str(v["effective_from"]) <= str(as_of)[:10]]
    if not valid:
        raise ValueError(f"No NBG rule version in force on {as_of}")
    return valid[-1]


def pti_limit(income_gel, loan_ccy, income_ccy, version: dict):
    """Vectorised PTI limit. 'Hedged' = GEL loan, or loan in the same currency as income."""
    income_gel = np.asarray(income_gel, dtype=float)
    loan_ccy, income_ccy = np.asarray(loan_ccy), np.asarray(income_ccy)
    p = version["pti"]
    below = income_gel < p["income_threshold_gel"]
    hedged = (loan_ccy == "GEL") | (loan_ccy == income_ccy)
    lim_below = np.where(hedged, p["below"]["hedged"], p["below"]["unhedged"])
    lim_above = np.where(hedged, p["above"]["hedged"], p["above"]["unhedged"])
    return np.where(below, lim_below, lim_above)


def ltv_limit(loan_ccy, version: dict):
    return np.where(np.asarray(loan_ccy) == "GEL", version["ltv"]["gel"], version["ltv"]["fx"])


def principal_for_payment(payment, annual_rate, term_months):
    r = np.asarray(annual_rate, dtype=float) / 12.0
    return np.asarray(payment, dtype=float) * (1 - (1 + r) ** -np.asarray(term_months, dtype=float)) / r


def check(income_gel, other_debt, payment, amount, loan_ccy, income_ccy, annual_rate, term_months,
          collateral=None, as_of: str = "2026-10-20", cfg: dict | None = None) -> dict:
    """Vectorised compliance check + maximum compliant loan for the requested term."""
    v = version_for(as_of, cfg)
    income_gel = np.maximum(np.asarray(income_gel, dtype=float), 1.0)
    lim = pti_limit(income_gel, loan_ccy, income_ccy, v)
    pti = (np.asarray(other_debt) + np.asarray(payment)) / income_gel
    max_pay = np.maximum(lim * income_gel - np.asarray(other_debt), 0.0)
    max_amt_pti = principal_for_payment(max_pay, annual_rate, term_months)
    out = {"rules_version": v["id"], "pti": pti, "pti_limit": lim, "pti_pass": pti <= lim + 1e-9,
           "max_payment": max_pay, "max_amount": max_amt_pti}
    if collateral is not None:
        coll = np.asarray(collateral, dtype=float)
        has = ~np.isnan(coll)
        llim = ltv_limit(loan_ccy, v)
        ltv = np.where(has, np.asarray(amount) / np.where(has, coll, 1.0), np.nan)
        out.update(ltv=ltv, ltv_limit=llim, ltv_pass=np.where(has, ltv <= llim + 1e-9, True))
        out["max_amount"] = np.where(has, np.minimum(max_amt_pti, llim * np.where(has, coll, 0)), max_amt_pti)
    return out
