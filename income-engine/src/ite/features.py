"""Turn categorised transactions into borrower-level features.

Works for one borrower (API / app) or thousands (training) with the same code path.
Input transactions need: tx_id, borrower_id, date, amount, currency, counterparty, cat.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .synth import USD_GEL

INCOME_CATS = ["salary", "harvest", "p2p_in", "remittance"]
EMPLOYMENT = {"salaried_tbilisi": "salaried", "young_first_loan": "salaried_young",
              "farmer_kakheti": "farmer", "self_employed": "self_employed", "remittance_hh": "remittance"}
EMP_TYPES = ["salaried", "salaried_young", "farmer", "self_employed", "remittance"]

FEATURES = [
    "inc_mean", "inc_median", "inc_p25", "inc_min3", "inc_cv", "season_top3", "n_income_months",
    "inc_yoy", "remit_share", "salary_share", "harvest_share", "p2p_share", "n_income_cp",
    "naive_inflow_mean", "betting_share", "late_util_rate", "savings_rate", "loan_repay_mean",
    "spend_ratio", "one_off_count", "own_transfer_count", "circular_ratio", "p2p_out_share",
    "spend_mean", "savings_mean", "outflow_mean",
]


def detect_round_trips(tx: pd.DataFrame, window_days: int = 7, tol: float = 0.05) -> set:
    """Inflows sent back to the same counterparty within a few days (income faking)."""
    # category-agnostic: a mislabelled line must not hide a circular transfer; own accounts excluded
    ext = ~tx["counterparty"].astype(str).str.startswith("SELF")
    ins = tx.loc[ext & (tx["amount"] > 0), ["tx_id", "borrower_id", "counterparty", "date", "amount"]]
    outs = tx.loc[ext & (tx["amount"] < 0), ["borrower_id", "counterparty", "date", "amount"]]
    m = ins.merge(outs, on=["borrower_id", "counterparty"], suffixes=("", "_out"))
    if m.empty:
        return set()
    dd = (m["date_out"] - m["date"]).dt.days
    ok = (dd >= 0) & (dd <= window_days) & ((m["amount"] + m["amount_out"]).abs() <= tol * m["amount"])
    return set(m.loc[ok, "tx_id"])


def _prep(tx: pd.DataFrame, app_dates: pd.Series) -> pd.DataFrame:
    t = tx.copy()
    t["date"] = pd.to_datetime(t["date"])
    t["gel"] = np.where(t["currency"] == "USD", t["amount"] * USD_GEL, t["amount"])
    app = pd.to_datetime(app_dates.reindex(t["borrower_id"]).to_numpy())
    t["off"] = (app.year * 12 + app.month) - (t["date"].dt.year * 12 + t["date"].dt.month)
    t["circular"] = t["tx_id"].isin(detect_round_trips(t))
    return t[(t["off"] >= 1) & (t["off"] <= 18)]


def monthly_income(t: pd.DataFrame, ids) -> pd.DataFrame:
    inc = t[t["cat"].isin(INCOME_CATS) & (t["gel"] > 0) & ~t["circular"]]
    mi = inc.pivot_table(index="borrower_id", columns="off", values="gel", aggfunc="sum", fill_value=0.0)
    return mi.reindex(index=ids, columns=range(1, 19), fill_value=0.0)


def calendar_profile(mi: pd.DataFrame, app_dates: pd.Series) -> np.ndarray:
    """Average income per calendar month (Jan..Dec) over the last 12 months, per borrower."""
    out = np.zeros((len(mi), 12))
    app = pd.to_datetime(app_dates.reindex(mi.index).to_numpy())
    for off in range(1, 13):
        cal = ((app.month - 1 - off) % 12).to_numpy()          # month index of that offset
        out[np.arange(len(mi)), cal] += mi[off].to_numpy()
    return out


def build(tx: pd.DataFrame, apps: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """apps: borrower_id, application_date, declared_income_gel, ... -> (features, calendar profiles)."""
    ids = apps["borrower_id"].to_numpy()
    app_dates = apps.set_index("borrower_id")["application_date"]
    t = _prep(tx, app_dates)
    mi = monthly_income(t, ids)
    last = mi[list(range(12, 0, -1))].to_numpy()                 # oldest -> newest
    tot = last.sum(1)
    mean = tot / 12
    roll3 = np.lib.stride_tricks.sliding_window_view(last, 3, axis=1).sum(-1)
    top3 = np.sort(last, 1)[:, -3:].sum(1)

    t12 = t[t["off"] <= 12]
    by = t12.pivot_table(index="borrower_id", columns="cat", values="gel", aggfunc="sum", fill_value=0.0).reindex(ids, fill_value=0.0)
    cnt = t12.pivot_table(index="borrower_id", columns="cat", values="gel", aggfunc="count", fill_value=0).reindex(ids, fill_value=0)
    col = lambda df, c: df[c].to_numpy() if c in df else np.zeros(len(ids))
    inc_t12 = t12[t12["cat"].isin(INCOME_CATS) & (t12["gel"] > 0) & ~t12["circular"]]
    util = t12[t12["cat"] == "utilities"]
    late = (util["date"].dt.day > 19).groupby(util["borrower_id"]).mean().reindex(ids, fill_value=0.0)
    circ = t12[t12["circular"] & (t12["gel"] > 0)].groupby("borrower_id")["gel"].sum().reindex(ids, fill_value=0.0)
    p2p_all = t12[(t12["gel"] > 0) & (t12["cat"] != "own_transfer")].groupby("borrower_id")["gel"].sum().reindex(ids, fill_value=0.0)
    first6 = mi[list(range(13, 19))].to_numpy().mean(1)
    recent6 = mi[list(range(1, 7))].to_numpy().mean(1)
    safe = np.maximum(tot, 1.0)

    f = pd.DataFrame({
        "inc_mean": mean,
        "inc_median": np.median(last, 1),
        "inc_p25": np.quantile(last, 0.25, axis=1),
        "inc_min3": roll3.min(1) / 3,
        "inc_cv": last.std(1) / np.maximum(mean, 1.0),
        "season_top3": top3 / safe,
        "n_income_months": (last > 0).sum(1),
        "inc_yoy": np.where(first6 > 0, recent6 / np.maximum(first6, 1.0), 1.0),
        "remit_share": col(by, "remittance") / safe,
        "salary_share": col(by, "salary") / safe,
        "harvest_share": col(by, "harvest") / safe,
        "p2p_share": (col(by, "p2p_in") - circ.to_numpy()) / safe,
        "n_income_cp": inc_t12.groupby("borrower_id")["counterparty"].nunique().reindex(ids, fill_value=0).to_numpy(),
        "naive_inflow_mean": t12[t12["gel"] > 0].groupby("borrower_id")["gel"].sum().reindex(ids, fill_value=0.0).to_numpy() / 12,
        "betting_share": -col(by, "betting") / safe,
        "late_util_rate": late.to_numpy(),
        "savings_rate": -col(by, "savings") / safe,
        "loan_repay_mean": -col(by, "loan_repayment") / 12,
        "spend_ratio": -col(by, "card_spend") / safe,
        "one_off_count": col(cnt, "one_off_in"),
        "own_transfer_count": col(cnt, "own_transfer"),
        "circular_ratio": circ.to_numpy() / np.maximum(p2p_all.to_numpy(), 1.0),
        "p2p_out_share": -col(by, "p2p_out") / safe,
        # absolute spending reveals income the bank cannot see (cash, other banks)
        "spend_mean": -col(by, "card_spend") / 12,
        "savings_mean": -col(by, "savings") / 12,
        "outflow_mean": -t12[(t12["gel"] < 0) & (t12["cat"] != "own_transfer") & ~t12["circular"]]
                         .groupby("borrower_id")["gel"].sum().reindex(ids, fill_value=0.0).to_numpy() / 12,
    }, index=pd.Index(ids, name="borrower_id"))
    return f, calendar_profile(mi, app_dates)


def application_frame(apps: pd.DataFrame) -> pd.DataFrame:
    """Fields a bank has from the application form (employment type is self-reported)."""
    a = apps.set_index("borrower_id")
    out = pd.DataFrame(index=a.index)
    out["declared_income"] = a["declared_income_gel"]
    out["declared_debt"] = a["existing_debt_payment_declared"]
    emp = a["employment_type"] if "employment_type" in a else a["archetype"].map(EMPLOYMENT)
    for e in EMP_TYPES:
        out[f"emp_{e}"] = (emp == e).astype(int)
    return out
