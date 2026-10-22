"""Decision engine: one code path for the API, the officer app and batch evaluation."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import categorise, features, rules, schedule
from .explain import Explainer, borrower_letter
from .models import risk_frame
from .synth import annuity

MODEL_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[2]


class Engine:
    def __init__(self, models_dir: str | Path = ROOT / "models", rules_path: str | Path = rules.DEFAULT_PATH):
        art = joblib.load(Path(models_dir) / "engine.joblib")
        self.cat_model = art["categoriser"]
        self.income = art["income"]
        self.risk = art["risk"]
        self.meta = art.get("meta", {})
        self.cfg = rules.load(str(rules_path))
        self.policy = self.cfg["policy"]
        self.explainer = Explainer(self.risk)

    # ---------------------------------------------------------------- batch
    def assess_batch(self, apps: pd.DataFrame, tx: pd.DataFrame, as_of: str | None = None,
                     categorised: bool = False) -> tuple[pd.DataFrame, dict]:
        """apps: one row per application. Returns (decisions table, intermediates)."""
        apps = apps.copy()
        if "employment_type" not in apps and "archetype" in apps:
            apps["employment_type"] = apps["archetype"].map(features.EMPLOYMENT)
        t = tx if categorised else tx.assign(cat=categorise.predict(self.cat_model, tx))
        feat, profile = features.build(t, apps)
        X = feat.join(features.application_frame(apps))
        inc = self.income.predict(X)
        a = apps.set_index("borrower_id").reindex(feat.index)
        q = f"inc_q{int(self.policy['income_quantile_for_pti'] * 100)}"
        debt = np.maximum(feat["loan_repay_mean"], a["existing_debt_payment_declared"])
        as_of = as_of or str(a["application_date"].max())
        req_amt, req_pay = a["loan_amount_gel"], a["monthly_payment_gel"]

        chk = rules.check(inc[q], debt, req_pay, req_amt, a["loan_currency"], a["income_currency"],
                          a["annual_rate"], a["term_months"], a["collateral_value_gel"], as_of, self.cfg)
        offer_amt = np.minimum(req_amt, np.floor(chk["max_amount"] / 100) * 100)
        no_offer = offer_amt < self.policy["min_loan_gel"]
        offer_amt = np.where(no_offer, 0.0, offer_amt)
        offer_pay = np.where(no_offer, 0.0, annuity(offer_amt, a["annual_rate"], a["term_months"]))

        Xr_req = risk_frame(feat, inc, a, req_pay, req_amt)
        Xr_off = risk_frame(feat, inc, a, pd.Series(np.where(no_offer, req_pay, offer_pay), index=feat.index),
                            pd.Series(np.where(no_offer, req_amt, offer_amt), index=feat.index))
        pd_req = self.risk.predict(Xr_req)
        pd_off = self.risk.predict(Xr_off)
        fx = Xr_off["fx_mismatch"].to_numpy() == 1
        Xs = Xr_off.copy()
        stress_pay = np.where(fx, np.where(no_offer, req_pay, offer_pay) * 1.2, np.where(no_offer, req_pay, offer_pay))
        Xs[["pti_est", "stress_est", "burden_p25"]] = risk_frame(feat, inc, a, pd.Series(stress_pay, index=feat.index),
                                                                 pd.Series(np.where(no_offer, req_amt, offer_amt), index=feat.index))[["pti_est", "stress_est", "burden_p25"]]
        pd_stress = self.risk.predict(Xs)

        band = ((inc["inc_q90"] - inc["inc_q10"]) / inc["inc_q50"]).to_numpy()
        circ = feat["circular_ratio"].to_numpy()
        P = self.policy
        rec = np.where(no_offer, "REJECT",
              np.where(pd_off >= P["pd_reject_min"], "REJECT",
              np.where((circ > P["round_trip_review"]) | (band > P["band_width_review"]) | (pd_off >= P["pd_approve_max"]), "REVIEW",
              np.where(offer_amt < req_amt, "APPROVE_REDUCED", "APPROVE"))))

        d = pd.DataFrame({
            "borrower_id": feat.index, "requested_amount": req_amt.to_numpy(), "offer_amount": offer_amt,
            "offer_payment": np.round(offer_pay, 2), "term_months": a["term_months"].to_numpy(),
            "declared_income": a["declared_income_gel"].to_numpy(), "existing_debt": np.round(debt.to_numpy(), 2),
            "annual_rate": a["annual_rate"].to_numpy(), "loan_currency": a["loan_currency"].to_numpy(),
            "income_currency": a["income_currency"].to_numpy(),
            **{c: inc[c].to_numpy().round(0) for c in inc.columns},
            "pti_requested": np.round(chk["pti"], 4), "pti_limit": chk["pti_limit"], "pti_pass": chk["pti_pass"],
            "ltv": chk.get("ltv"), "ltv_limit": chk.get("ltv_limit"), "ltv_pass": chk.get("ltv_pass"),
            "max_compliant_amount": np.floor(chk["max_amount"] / 100) * 100,
            "pd_requested": pd_req.round(4), "pd_offer": pd_off.round(4), "pd_gel_minus20": pd_stress.round(4),
            "band_width": band.round(3), "circular_ratio": circ.round(3),
            "seasonal": feat["season_top3"].to_numpy() >= 0.45, "thin_file": a["thin_file"].to_numpy(),
            "recommendation": rec, "rules_version": chk["rules_version"], "model_version": MODEL_VERSION,
        })
        return d, {"features": feat, "X": X, "income": inc, "risk_X": Xr_off, "profile": profile, "apps": a}

    # ---------------------------------------------------------------- single application
    def assess(self, app: dict, tx: pd.DataFrame, as_of: str | None = None) -> dict:
        apps = pd.DataFrame([app])
        d, mid = self.assess_batch(apps, tx.assign(borrower_id=app["borrower_id"]), as_of)
        row = d.iloc[0]
        bid = row["borrower_id"]
        Xr = mid["risk_X"].loc[[bid]]
        reasons = self.explainer.reasons(Xr)
        a = mid["apps"].loc[bid]
        offer_amt = float(row["offer_amount"])
        term, rate = int(a["term_months"]), float(a["annual_rate"])
        start_month = (pd.Timestamp(a["application_date"]).month % 12) + 1
        alternatives = []
        q = f"inc_q{int(self.policy['income_quantile_for_pti'] * 100)}"
        debt = float(max(mid["features"].loc[bid, "loan_repay_mean"], a["existing_debt_payment_declared"]))
        for t in sorted({12, 24, 36, 48, 60, term}):
            c = rules.check([mid["income"].loc[bid, q]], [debt], [0.0], [0.0], [a["loan_currency"]],
                            [a["income_currency"]], [rate], [t], None, as_of or str(a["application_date"]), self.cfg)
            alternatives.append({"term_months": t, "max_amount": float(np.floor(c["max_amount"][0] / 100) * 100)})
        seasonal = None
        if bool(row["seasonal"]) and offer_amt > 0:
            prof = mid["profile"][list(mid["features"].index).index(bid)]
            sched = schedule.seasonal_schedule(offer_amt, rate, term, prof, start_month)
            ann = schedule.annuity_schedule(offer_amt, rate, term)
            seasonal = {"payments_first_12": np.round(sched[:12], 2).tolist(),
                        "annuity_payment": round(float(ann[0]), 2),
                        "min_payment": round(float(sched.min()), 2), "max_payment": round(float(sched.max()), 2),
                        "income_profile_by_month": np.round(prof, 0).tolist(), "start_month": start_month,
                        "note": "Same present value as the annuity. Confirm PTI treatment of non-equal schedules with NBG."}
        flags = []
        if row["thin_file"]:
            flags.append("Thin file: no credit-bureau history")
        if row["circular_ratio"] > self.policy["round_trip_review"]:
            flags.append(f"Circular transfers: {row['circular_ratio']:.0%} of client inflows are sent back")
        if row["band_width"] > self.policy["band_width_review"]:
            flags.append("Wide income uncertainty band")
        if not row["pti_pass"]:
            flags.append("Requested amount breaks NBG PTI limit")
        out = {k: (v.item() if hasattr(v, "item") else v) for k, v in row.to_dict().items()}
        out.update({"reasons": reasons, "alternatives": alternatives, "seasonal_schedule": seasonal, "flags": flags,
                    "offer": {"amount": offer_amt, "term_months": term, "monthly_payment": float(row["offer_payment"])},
                    "features": {k: float(v) for k, v in mid["features"].loc[bid].items()}})
        out["letter_ka"] = borrower_letter(out, "ka")
        out["letter_en"] = borrower_letter(out, "en")
        return _clean(out)


def _clean(o):
    """JSON-safe: NaN/inf -> None, numpy scalars -> Python."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
