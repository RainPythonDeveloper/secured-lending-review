"""Transaction categoriser for mixed Georgian / Latin bank descriptions.

Character n-grams work on Georgian script without a tokenizer or a translation step,
so the model does not depend on an LLM that may perform worse in Georgian.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

TEXT = "description"


COLS = [TEXT, "currency", "amount", "date", "cp_count", "cp_months", "is_own"]


def context(tx: pd.DataFrame) -> pd.DataFrame:
    """Behavioural context a bank has for every line: how often this counterparty recurs for the
    customer, in how many months, and whether it is one of the customer's own accounts."""
    t = tx.copy()
    d = pd.to_datetime(t["date"])
    g = t.groupby(["borrower_id", "counterparty"])
    t["cp_count"] = g["amount"].transform("size")
    t["cp_months"] = (d.dt.year * 12 + d.dt.month).groupby([t["borrower_id"], t["counterparty"]]).transform("nunique")
    t["is_own"] = t["counterparty"].astype(str).str.startswith("SELF").astype(int)
    return t


def _numeric(df: pd.DataFrame) -> np.ndarray:
    amt = df["amount"].to_numpy(dtype=float)
    day = pd.to_datetime(df["date"]).dt.day.to_numpy()
    return np.column_stack([np.sign(amt), np.log1p(np.abs(amt)) / 10, day / 31,
                            np.log1p(df["cp_count"].to_numpy()) / 4, df["cp_months"].to_numpy() / 18,
                            df["is_own"].to_numpy()])


def build() -> Pipeline:
    pre = ColumnTransformer([
        ("txt", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True), TEXT),
        ("ccy", OneHotEncoder(handle_unknown="ignore"), ["currency"]),
        ("num", FunctionTransformer(_numeric), ["amount", "date", "cp_count", "cp_months", "is_own"]),
    ])
    return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=3000, C=4.0))])


def fit(tx: pd.DataFrame, sample: int = 150_000, seed: int = 0) -> Pipeline:
    s = context(tx).sample(min(sample, len(tx)), random_state=seed)
    model = build()
    model.fit(s[COLS], s["category_true"])
    return model


def predict(model: Pipeline, tx: pd.DataFrame) -> np.ndarray:
    return model.predict(context(tx)[COLS])
