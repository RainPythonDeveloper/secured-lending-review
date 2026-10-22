"""Income quantile model, risk model (LightGBM + isotonic calibration), challenger and baseline."""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import EMP_TYPES, FEATURES

warnings.filterwarnings("ignore", message="X does not have valid feature names")
warnings.filterwarnings("ignore", category=UserWarning, module="shap")
warnings.filterwarnings("ignore", message=".*eval_set.*")

QUANTILES = (0.10, 0.25, 0.50, 0.90)
INCOME_FEATURES = FEATURES + ["declared_income", "declared_debt"] + [f"emp_{e}" for e in EMP_TYPES]


class IncomeModel:
    """Predicts true monthly income (GEL) at several quantiles -> estimate with an uncertainty band.

    In production the training label is *verified* income (payroll, Revenue Service
    declarations or documents) for a subset of customers; here it is the synthetic truth.
    """

    def __init__(self, seed: int = 0):
        self.models = {q: lgb.LGBMRegressor(objective="quantile", alpha=q, n_estimators=500, learning_rate=0.03,
                                            num_leaves=31, min_child_samples=30, subsample=0.8, subsample_freq=1,
                                            colsample_bytree=0.8, random_state=seed, verbose=-1)
                       for q in QUANTILES}

    def fit(self, X: pd.DataFrame, income: np.ndarray, calib_share: float = 0.25, seed: int = 0) -> "IncomeModel":
        """Split-conformal calibration: quantile models are fitted on one part of the data and
        their quantiles are shifted on a held-out part so that stated coverage is actually met."""
        y = np.log(np.maximum(np.asarray(income, float), 50))
        rng = np.random.default_rng(seed)
        cal = rng.random(len(y)) < calib_share
        for m in self.models.values():
            m.fit(X[INCOME_FEATURES][~cal], y[~cal])
        self.shift = {}
        for q, m in self.models.items():
            resid = y[cal] - m.predict(X[INCOME_FEATURES][cal])   # want P(y <= q_hat + s) = q
            self.shift[q] = float(np.quantile(resid, q))
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        P = np.column_stack([np.exp(self.models[q].predict(X[INCOME_FEATURES]) + getattr(self, "shift", {}).get(q, 0.0))
                             for q in QUANTILES])
        P = np.sort(P, axis=1)                                   # enforce non-crossing quantiles
        return pd.DataFrame(P, index=X.index, columns=[f"inc_q{int(q * 100)}" for q in QUANTILES])


RISK_FEATURES = [
    "pti_est", "stress_est", "burden_p25", "inc_cv", "season_top3", "n_income_months", "inc_yoy",
    "remit_share", "betting_share", "late_util_rate", "savings_rate", "spend_ratio", "circular_ratio",
    "band_width", "declared_gap", "fx_mismatch", "term_months", "annual_rate", "loan_to_income",
    "bureau_score", "thin_file", "one_off_count",
]
# Business-logic monotonicity: model risk teams can sign this off; it cannot learn "more debt = safer".
MONOTONE = {"pti_est": 1, "stress_est": 1, "burden_p25": 1, "betting_share": 1, "late_util_rate": 1,
            "savings_rate": -1, "circular_ratio": 1, "fx_mismatch": 1, "bureau_score": -1}


def risk_frame(feat: pd.DataFrame, inc: pd.DataFrame, app: pd.DataFrame, payment: pd.Series,
               amount: pd.Series) -> pd.DataFrame:
    """Risk features for a given offer (payment / amount), so offers can be re-scored."""
    a = app.reindex(feat.index)
    debt = np.maximum(feat["loan_repay_mean"], a["existing_debt_payment_declared"])
    p50, p25 = inc["inc_q50"], inc["inc_q25"]
    stress_base = np.maximum(feat["inc_min3"] * (p50 / np.maximum(feat["inc_mean"], 1.0)), 50.0)
    return pd.DataFrame({
        "pti_est": (debt + payment) / p50,
        "stress_est": (debt + payment) / stress_base,
        "burden_p25": (debt + payment) / p25,
        "inc_cv": feat["inc_cv"], "season_top3": feat["season_top3"], "n_income_months": feat["n_income_months"],
        "inc_yoy": feat["inc_yoy"], "remit_share": feat["remit_share"], "betting_share": feat["betting_share"],
        "late_util_rate": feat["late_util_rate"], "savings_rate": feat["savings_rate"],
        "spend_ratio": feat["spend_ratio"], "circular_ratio": feat["circular_ratio"],
        "band_width": (inc["inc_q90"] - inc["inc_q10"]) / p50,
        "declared_gap": a["declared_income_gel"] / p50 - 1.0,
        "fx_mismatch": ((a["loan_currency"] == "USD") & (a["income_currency"] == "GEL")).astype(int),
        "term_months": a["term_months"], "annual_rate": a["annual_rate"],
        "loan_to_income": amount / p50,
        "bureau_score": a["bureau_score"], "thin_file": a["thin_file"].astype(int),
        "one_off_count": feat["one_off_count"],
    }, index=feat.index)[RISK_FEATURES]


class RiskModel:
    """Champion-challenger risk model.

    Two candidates are trained on the same features: a transparent logistic scorecard and a
    monotone-constrained LightGBM. The simpler scorecard is champion unless the GBM beats it on
    the validation set by more than `min_gain` AUC (model-risk principle: no unexplained complexity).
    """

    def __init__(self, seed: int = 0, min_gain: float = 0.005):
        mono = [MONOTONE.get(c, 0) for c in RISK_FEATURES]
        self.lgbm = lgb.LGBMClassifier(n_estimators=3000, learning_rate=0.03, num_leaves=4, min_child_samples=150,
                                       subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=10.0,
                                       monotone_constraints=mono, monotone_constraints_method="advanced",
                                       random_state=seed, verbose=-1)
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999)
        self.scorecard = Challenger()
        self.min_gain = min_gain
        self.champion = "scorecard"
        self.validation = {}

    def fit(self, X: pd.DataFrame, y: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> "RiskModel":
        from sklearn.metrics import roc_auc_score
        self.lgbm.fit(X[RISK_FEATURES], y, eval_set=[(X_val[RISK_FEATURES], y_val)], eval_metric="auc",
                      callbacks=[lgb.early_stopping(150, verbose=False)])
        self.iso.fit(self.raw_gbm(X_val), y_val)
        self.scorecard.fit(X, y)
        auc_gbm = roc_auc_score(y_val, self.raw_gbm(X_val))
        auc_sc = roc_auc_score(y_val, self.scorecard.predict(X_val))
        self.champion = "gbm" if auc_gbm - auc_sc > self.min_gain else "scorecard"
        self.validation = {"auc_gbm": round(float(auc_gbm), 4), "auc_scorecard": round(float(auc_sc), 4),
                           "champion": self.champion, "min_gain_required": self.min_gain}
        # final scorecard uses all development data
        self.scorecard.fit(pd.concat([X, X_val]), np.concatenate([y, y_val]))
        return self

    def raw_gbm(self, X: pd.DataFrame) -> np.ndarray:
        return self.lgbm.predict_proba(X[RISK_FEATURES])[:, 1]

    def predict_gbm(self, X: pd.DataFrame) -> np.ndarray:
        return self.iso.predict(self.raw_gbm(X))

    def predict_scorecard(self, X: pd.DataFrame) -> np.ndarray:
        return self.scorecard.predict(X)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.predict_gbm(X) if self.champion == "gbm" else self.predict_scorecard(X)


# Expected direction of each feature's effect on default risk (business logic, signed off by risk).
EXPECTED_SIGN = {**MONOTONE, "inc_cv": 1, "band_width": 1, "loan_to_income": 1, "spend_ratio": 1,
                 "declared_gap": 1, "season_top3": 1, "annual_rate": 1, "thin_file": 1,
                 "n_income_months": -1, "inc_yoy": -1}


class Challenger:
    """Transparent logistic scorecard with sign-constrained feature selection: any feature whose
    fitted effect contradicts business logic is removed and logged, then the model is refitted."""

    def __init__(self, C: float = 0.5):
        self.C = C
        self.features = list(RISK_FEATURES)
        self.dropped: list[dict] = []

    def _pipe(self):
        return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                             LogisticRegression(max_iter=3000, C=self.C))

    def fit(self, X, y):
        self.features, self.dropped = list(RISK_FEATURES), []
        for _ in range(len(RISK_FEATURES)):
            self.m = self._pipe().fit(X[self.features], y)
            co = self.coefficients()
            bad = {f: co[f] for f in self.features
                   if f in EXPECTED_SIGN and f in co and np.sign(co[f]) == -EXPECTED_SIGN[f]}
            if not bad:
                break
            worst = max(bad, key=lambda f: abs(bad[f]))
            self.dropped.append({"feature": worst, "coef": round(float(bad[worst]), 3),
                                 "expected": "+" if EXPECTED_SIGN[worst] > 0 else "-"})
            self.features.remove(worst)
        return self

    def predict(self, X):
        return self.m.predict_proba(X[self.features])[:, 1]

    def coefficients(self) -> pd.Series:
        names = self.m[:-1].get_feature_names_out(self.features)
        return pd.Series(self.m[-1].coef_[0], index=names).sort_values()

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Exact log-odds contribution of each original feature vs. an average applicant
        (equals SHAP values for a linear model with standardised inputs). Dropped features = 0."""
        Z = self.m[:-1].transform(X[self.features])
        c = Z * self.m[-1].coef_[0]
        names = list(self.m[:-1].get_feature_names_out(self.features))
        out = np.zeros((len(X), len(RISK_FEATURES)))
        for j, nm in enumerate(names):
            base = nm.replace("missingindicator_", "")
            out[:, RISK_FEATURES.index(base)] += c[:, j]
        return out


class TraditionalBaseline:
    """What lenders do today: bureau score + declared income only."""

    def __init__(self):
        self.m = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                               LogisticRegression(max_iter=1000))

    @staticmethod
    def frame(app: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({
            "bureau_score": app["bureau_score"],
            "declared_pti": (app["monthly_payment_gel"] + app["existing_debt_payment_declared"]) / app["declared_income_gel"],
            "thin_file": app["thin_file"].astype(int),
        }, index=app.index)

    def fit(self, app, y):
        self.m.fit(self.frame(app), y)
        return self

    def predict(self, app):
        return self.m.predict_proba(self.frame(app))[:, 1]
