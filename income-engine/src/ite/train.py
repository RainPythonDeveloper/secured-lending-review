"""End-to-end training and evaluation.

    python -m ite.train            # generates data if missing, trains, evaluates, writes models/ and reports/

Train on cohort A (applications Jul-2025), test out-of-time on cohort B (Jul-2026).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fairlearn.metrics import MetricFrame, selection_rate
from sklearn.metrics import (accuracy_score, brier_score_loss, classification_report, f1_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import train_test_split

from . import categorise, features, rules, schedule, synth
from .engine import Engine, MODEL_VERSION
from .models import EXPECTED_SIGN, MONOTONE, RISK_FEATURES, IncomeModel, RiskModel, TraditionalBaseline, risk_frame

ROOT = Path(__file__).resolve().parents[2]
DATA, MODELS, REPORTS = ROOT / "data", ROOT / "models", ROOT / "reports"


def ks(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def scores(y, p) -> dict:
    auc = roc_auc_score(y, p)
    return {"auc": round(float(auc), 4), "gini": round(float(2 * auc - 1), 4), "ks": round(ks(y, p), 4),
            "brier": round(float(brier_score_loss(y, p)), 4), "mean_pd": round(float(np.mean(p)), 4),
            "default_rate": round(float(np.mean(y)), 4)}


def mdape(est, true):
    return float(np.median(np.abs(est - true) / true))


def psi(a, b, bins=10):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    edges = np.unique(np.quantile(a, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    ea = np.histogram(np.clip(a, edges[0], edges[-1]), edges)[0] / len(a) + 1e-6
    eb = np.histogram(np.clip(b, edges[0], edges[-1]), edges)[0] / len(b) + 1e-6
    return float(np.sum((eb - ea) * np.log(eb / ea)))


def true_pd_at(bor: pd.DataFrame, payments12: np.ndarray) -> np.ndarray:
    """Ground-truth PD if the borrower had received this 12-month payment path (evaluation only)."""
    other = bor["TRUE_other_payment"].to_numpy()
    ti = bor["TRUE_income_gel"].to_numpy()
    start = pd.to_datetime(bor["application_date"]).dt.month.to_numpy() % 12 + 1
    stress = np.empty(len(bor))
    for i, (arch, inc, s) in enumerate(zip(bor["archetype"], ti, start)):
        prof = np.roll(synth.expected_profile(arch, inc), -(s - 1))
        stress[i] = synth.liquidity_stress(other[i] + payments12[i], prof)
    burden = (other + payments12.mean(1)) / ti
    fx = ((bor["loan_currency"] == "USD") & (bor["income_currency"] == "GEL")).to_numpy()
    drift = np.where(bor["cohort"] == "B", 0.15, 0.0)
    return synth.sigmoid(synth.true_logit(burden, stress, fx, bor["TRUE_gamble_share"].to_numpy(),
                                          bor["TRUE_late_rate"].to_numpy(), bor["TRUE_fragility"].to_numpy(),
                                          bor["TRUE_shock"].to_numpy(), bor["TRUE_savings_rate"].to_numpy(), drift))


def main(seed: int = 42):
    t0 = time.time()
    MODELS.mkdir(exist_ok=True)
    (REPORTS).mkdir(exist_ok=True)
    if not (DATA / "borrowers.csv").exists():
        synth.save(synth.generate(8000, seed), DATA)
    bor = pd.read_csv(DATA / "borrowers.csv")
    tx = pd.read_parquet(DATA / "transactions.parquet")
    card = json.loads((DATA / "data_card.json").read_text())
    bor["employment_type"] = bor["archetype"].map(features.EMPLOYMENT)
    A, B = bor[bor.cohort == "A"], bor[bor.cohort == "B"]
    M: dict = {"generated_at": time.strftime("%Y-%m-%d %H:%M"), "model_version": MODEL_VERSION, "data": card}

    # 1. categoriser -----------------------------------------------------------------
    txA = tx[tx.borrower_id.isin(A.borrower_id)]
    txB = tx[tx.borrower_id.isin(B.borrower_id)]
    cat = categorise.fit(txA, seed=seed)
    predB = pd.Series(categorise.predict(cat, txB), index=txB.index)
    sB = txB.sample(200_000, random_state=seed)
    pB = predB.loc[sB.index].to_numpy()
    M["categoriser"] = {"accuracy": round(accuracy_score(sB.category_true, pB), 4),
                        "macro_f1": round(f1_score(sB.category_true, pB, average="macro"), 4),
                        "per_class_f1": {k: round(v["f1-score"], 4) for k, v in
                                         classification_report(sB.category_true, pB, output_dict=True).items()
                                         if k not in ("accuracy", "macro avg", "weighted avg")}}
    tx = tx.assign(cat=categorise.predict(cat, tx))
    rt_ids = features.detect_round_trips(tx.assign(date=pd.to_datetime(tx.date)))
    rt_true = set(tx.loc[tx.is_round_trip & (tx.amount > 0), "tx_id"])
    M["round_trip_detection"] = {"precision": round(len(rt_ids & rt_true) / max(len(rt_ids), 1), 4),
                                 "recall": round(len(rt_ids & rt_true) / max(len(rt_true), 1), 4)}

    # 2. features ----------------------------------------------------------------------
    feat, profile = features.build(tx, bor)
    X = feat.join(features.application_frame(bor))
    b = bor.set_index("borrower_id").loc[feat.index]
    iA, iB = b.cohort.eq("A").to_numpy(), b.cohort.eq("B").to_numpy()

    # 3. income model -----------------------------------------------------------------
    inc_model = IncomeModel(seed).fit(X[iA], b.TRUE_income_gel[iA].to_numpy())
    inc = inc_model.predict(X)
    true_inc = b.TRUE_income_gel
    tB = true_inc[iB]
    cover = ((tB >= inc.inc_q10[iB]) & (tB <= inc.inc_q90[iB])).mean()
    by_arch = {}
    for arch, g in b[iB].groupby("archetype"):
        ix = g.index
        by_arch[arch] = {"declared": round(mdape(g.declared_income_gel, g.TRUE_income_gel), 4),
                         "naive_inflows": round(mdape(feat.loc[ix, "naive_inflow_mean"], g.TRUE_income_gel), 4),
                         "engine_p50": round(mdape(inc.loc[ix, "inc_q50"], g.TRUE_income_gel), 4), "n": int(len(g))}
    rtB = b[iB & b.TRUE_round_trip.to_numpy()].index
    M["income"] = {
        "mdape_declared": round(mdape(b.declared_income_gel[iB], tB), 4),
        "mdape_naive_inflows": round(mdape(feat.naive_inflow_mean[iB], tB), 4),
        "mdape_engine_p50": round(mdape(inc.inc_q50[iB], tB), 4),
        "band_coverage_p10_p90": round(float(cover), 4),
        "p25_below_true_share": round(float((inc.inc_q25[iB] <= tB).mean()), 4),
        "by_archetype": by_arch,
        "round_trippers": {"n": int(len(rtB)),
                           "declared_overstatement": round(float((b.loc[rtB, "declared_income_gel"] / b.loc[rtB, "TRUE_income_gel"]).median() - 1), 4),
                           "naive_overstatement": round(float((feat.loc[rtB, "naive_inflow_mean"] / b.loc[rtB, "TRUE_income_gel"]).median() - 1), 4),
                           "engine_overstatement": round(float((inc.loc[rtB, "inc_q50"] / b.loc[rtB, "TRUE_income_gel"]).median() - 1), 4)},
    }

    # 4. risk models (label = outcome under the requested loan) --------------------------
    Xr = risk_frame(feat, inc, b, b.monthly_payment_gel, b.loan_amount_gel)
    y = b.TRUE_default.astype(int).to_numpy()
    idxA = np.flatnonzero(iA)
    tr, va = train_test_split(idxA, test_size=0.25, random_state=seed, stratify=y[idxA])
    risk = RiskModel(seed).fit(Xr.iloc[tr], y[tr], Xr.iloc[va], y[va])
    chal = risk.scorecard
    base = TraditionalBaseline().fit(b.iloc[idxA], y[idxA])
    yB = y[iB]
    p_eng, p_base = risk.predict(Xr[iB]), base.predict(b[iB])
    p_sc, p_gbm = risk.predict_scorecard(Xr[iB]), risk.predict_gbm(Xr[iB])
    thinB = b.thin_file[iB].to_numpy()
    M["risk"] = {
        "engine": scores(yB, p_eng), "scorecard": scores(yB, p_sc), "gbm": scores(yB, p_gbm),
        "traditional_bureau": scores(yB, p_base), "champion_selection": risk.validation,
        "oracle_true_pd": scores(yB, b.TRUE_pd[iB].to_numpy()),
        "thin_file": {"engine": scores(yB[thinB], p_eng[thinB]), "traditional_bureau": scores(yB[thinB], p_base[thinB]),
                      "oracle_true_pd": scores(yB[thinB], b.TRUE_pd[iB].to_numpy()[thinB])},
        "with_bureau": {"engine": scores(yB[~thinB], p_eng[~thinB]),
                        "traditional_bureau": scores(yB[~thinB], p_base[~thinB])},
        "gbm_best_iteration": int(risk.lgbm.best_iteration_ or risk.lgbm.n_estimators),
        "scorecard_coefficients": {k: round(float(v), 3) for k, v in chal.coefficients().items()},
    }
    coefs = chal.coefficients()
    M["risk"]["sign_checks"] = {f: {"expected": "+" if sgn > 0 else "-", "coef": round(float(coefs.get(f, 0.0)), 3),
                                    "in_model": f in chal.features,
                                    "pass": bool(np.sign(coefs.get(f, 0.0)) in (sgn, 0))}
                                for f, sgn in EXPECTED_SIGN.items()}
    M["risk"]["scorecard_dropped_features"] = chal.dropped
    M["risk"]["share_of_oracle_gini"] = round(M["risk"]["engine"]["gini"] / M["risk"]["oracle_true_pd"]["gini"], 4)
    # calibration table (deciles)
    dec = pd.qcut(p_eng, 10, labels=False, duplicates="drop")
    M["risk"]["calibration"] = [{"bin": int(k), "predicted": round(float(p_eng[dec == k].mean()), 4),
                                 "observed": round(float(yB[dec == k].mean()), 4), "n": int((dec == k).sum())}
                                for k in np.unique(dec)]
    rc = {}
    for name, p in (("engine", p_eng), ("traditional_bureau", p_base), ("gbm", p_gbm)):
        fpr, tpr, _ = roc_curve(yB, p)
        sel = np.linspace(0, len(fpr) - 1, 60).astype(int)
        rc[name] = {"fpr": fpr[sel].round(4).tolist(), "tpr": tpr[sel].round(4).tolist()}
    M["risk"]["roc"] = rc

    # 5. save artifacts -----------------------------------------------------------------
    joblib.dump({"categoriser": cat, "income": inc_model, "risk": risk, "challenger": chal, "baseline": base,
                 "meta": {"version": MODEL_VERSION, "trained_on": "cohort A (synthetic)", "seed": seed}},
                MODELS / "engine.joblib", compress=3)

    # 6. engine decisions on the out-of-time cohort -------------------------------------------
    eng = Engine(MODELS)
    txB_c = tx[tx.borrower_id.isin(B.borrower_id)]
    t1 = time.time()
    dec_B, mid = eng.assess_batch(B, txB_c, categorised=True)
    batch_sec = time.time() - t1
    dec_B = dec_B.set_index("borrower_id")
    bB = b.loc[dec_B.index]

    # counterfactual ground truth for each offer
    def pay12(amount):
        return np.repeat(np.asarray(synth.annuity(amount, bB.annual_rate, bB.term_months))[:, None], 12, 1)
    dec_B["true_pd_offer"] = np.where(dec_B.offer_amount > 0, true_pd_at(bB, pay12(dec_B.offer_amount.to_numpy())), np.nan)
    dec_B["true_pd_requested"] = bB.TRUE_pd
    check_requested = np.abs(true_pd_at(bB, pay12(bB.loan_amount_gel.to_numpy())) - bB.TRUE_pd).max()
    M["sanity_counterfactual_max_error"] = float(round(check_requested, 6))

    # 7. policy comparison ---------------------------------------------------------------
    v = rules.version_for("2026-07-01")
    lim_decl = rules.pti_limit(bB.declared_income_gel, bB.loan_currency, bB.income_currency, v)
    decl_pti = (bB.monthly_payment_gel + bB.existing_debt_payment_declared) / bB.declared_income_gel
    lim_true = rules.pti_limit(bB.TRUE_income_gel, bB.loan_currency, bB.income_currency, v)

    def summarise(mask, amount, pd_true, label):
        mask = np.asarray(mask, bool)
        amt = np.asarray(amount, float)[mask]
        pdt = np.asarray(pd_true, float)[mask]
        pay = synth.annuity(amt, bB.annual_rate[mask], bB.term_months[mask])
        true_pti = (bB.TRUE_other_payment[mask] + pay) / bB.TRUE_income_gel[mask]
        return {"policy": label, "approved": int(mask.sum()), "approval_rate": round(float(mask.mean()), 4),
                "thin_file_approved": int((mask & bB.thin_file.to_numpy()).sum()),
                "thin_file_approval_rate": round(float(mask[bB.thin_file.to_numpy()].mean()), 4),
                "expected_bad_rate": round(float(pdt.mean()) if mask.any() else 0.0, 4),
                "volume_gel": round(float(amt.sum()), 0),
                "expected_loss_gel": round(float((pdt * amt * eng.policy["lgd"]).sum()), 0),
                "loss_rate": round(float((pdt * amt * eng.policy["lgd"]).sum() / max(amt.sum(), 1)), 4),
                "hidden_pti_breaches": int((true_pti > lim_true[mask] + 1e-9).sum()),
                "round_trippers_approved": int(bB.TRUE_round_trip.to_numpy()[mask].sum())}

    # Traditional: bureau cut-off, thin files declined, amount capped at the PTI limit on DECLARED income
    chk_t = rules.check(bB.declared_income_gel, bB.existing_debt_payment_declared, bB.monthly_payment_gel,
                        bB.loan_amount_gel, bB.loan_currency, bB.income_currency, bB.annual_rate, bB.term_months,
                        bB.collateral_value_gel, "2026-07-01")
    trad_amt = np.minimum(bB.loan_amount_gel, np.floor(chk_t["max_amount"] / 100) * 100).to_numpy()
    trad_amt = np.where(trad_amt < 500, 0.0, trad_amt)
    trad_pd = np.where(trad_amt > 0, true_pd_at(bB, pay12(trad_amt)), np.nan)
    trad_ok = (~bB.thin_file).to_numpy() & (trad_amt > 0)

    def trad_policy(cut):
        return trad_ok & (bB.bureau_score.to_numpy() >= cut)
    trad_mask = trad_policy(600)
    trad = summarise(trad_mask, trad_amt, trad_pd, "Traditional: bureau ≥ 600, declared-income PTI cap")
    auto = dec_B.recommendation.isin(["APPROVE", "APPROVE_REDUCED"]).to_numpy()
    eng_s = summarise(auto, dec_B.offer_amount, dec_B.true_pd_offer, "Engine: auto-recommended approvals")
    # engine at the same expected bad rate as traditional (threshold on PD of the offer)
    eligible = (dec_B.offer_amount > 0).to_numpy() & (dec_B.circular_ratio <= eng.policy["round_trip_review"]).to_numpy()
    order = np.argsort(dec_B.pd_offer.to_numpy())
    cum_bad = np.cumsum(np.nan_to_num(dec_B.true_pd_offer.to_numpy()[order]) * eligible[order]) / np.maximum(np.cumsum(eligible[order]), 1)
    target = trad["expected_bad_rate"]
    k = int(np.max(np.flatnonzero((cum_bad <= target) & (np.cumsum(eligible[order]) > 50)), initial=0))
    thr = float(dec_B.pd_offer.to_numpy()[order][k])
    match_mask = eligible & (dec_B.pd_offer.to_numpy() <= thr)
    eng_m = summarise(match_mask, dec_B.offer_amount, dec_B.true_pd_offer, "Engine at the same bad rate as traditional")
    eng_m["pd_threshold"] = round(thr, 4)
    M["policy"] = {"traditional": trad, "engine_auto": eng_s, "engine_matched": eng_m,
                   "recommendation_mix": dec_B.recommendation.value_counts(normalize=True).round(4).to_dict(),
                   "review_queue_share": round(float((dec_B.recommendation == "REVIEW").mean()), 4)}
    # approval vs bad-rate curves
    curves = {"engine": [], "traditional": []}
    for q in np.linspace(0.05, 0.95, 19):
        t_ = np.quantile(dec_B.pd_offer[eligible], q)
        m_ = eligible & (dec_B.pd_offer.to_numpy() <= t_)
        curves["engine"].append({"approval_rate": round(float(m_.mean()), 4),
                                 "bad_rate": round(float(dec_B.true_pd_offer.to_numpy()[m_].mean()), 4)})
    for c in range(400, 781, 20):
        m_ = trad_policy(c)
        if m_.sum() > 30:
            curves["traditional"].append({"approval_rate": round(float(m_.mean()), 4),
                                          "bad_rate": round(float(trad_pd[m_].mean()), 4)})
    M["policy"]["curves"] = curves

    # 8. harvest-shaped schedule for seasonal borrowers ------------------------------------
    seas = dec_B.index[(dec_B.seasonal) & (dec_B.offer_amount > 0)]
    if len(seas):
        pos = {bid: i for i, bid in enumerate(mid["features"].index)}
        p_ann, p_sea = [], []
        bS = bB.loc[seas]
        start = pd.to_datetime(bS.application_date).dt.month.to_numpy() % 12 + 1
        ann_m = np.zeros((len(seas), 12))
        sea_m = np.zeros((len(seas), 12))
        for i, bid in enumerate(seas):
            amt, r_, t_ = dec_B.at[bid, "offer_amount"], bS.at[bid, "annual_rate"], int(bS.at[bid, "term_months"])
            ann_m[i] = schedule.annuity_schedule(amt, r_, t_)[:12] if t_ >= 12 else np.resize(schedule.annuity_schedule(amt, r_, t_), 12)
            s_ = schedule.seasonal_schedule(amt, r_, t_, mid["profile"][pos[bid]], start[i])
            sea_m[i] = s_[:12] if t_ >= 12 else np.resize(s_, 12)
        p_ann, p_sea = true_pd_at(bS, ann_m), true_pd_at(bS, sea_m)
        M["seasonal"] = {"n": int(len(seas)), "true_pd_annuity": round(float(p_ann.mean()), 4),
                         "true_pd_seasonal": round(float(p_sea.mean()), 4),
                         "relative_reduction": round(float(1 - p_sea.mean() / p_ann.mean()), 4),
                         "example": {"borrower_id": int(seas[0]), "annuity": ann_m[0].round(0).tolist(),
                                     "seasonal": sea_m[0].round(0).tolist(),
                                     "start_month": int(start[0])}}

    # 9. fairness ---------------------------------------------------------------------
    age_band = pd.cut(bB.age, [0, 25, 40, 55, 100], labels=["18-25", "26-40", "41-55", "56+"]).astype(str)
    good = ~bB.TRUE_default.to_numpy()
    fair = {}
    for name, grp in (("region", bB.region), ("gender", bB.gender), ("age_band", age_band),
                      ("thin_file", bB.thin_file.map({True: "thin", False: "bureau"}))):
        mf_e = MetricFrame(metrics=selection_rate, y_true=good, y_pred=match_mask, sensitive_features=grp)
        mf_t = MetricFrame(metrics=selection_rate, y_true=good, y_pred=trad_mask, sensitive_features=grp)
        eo_e = MetricFrame(metrics=selection_rate, y_true=good[good], y_pred=match_mask[good], sensitive_features=grp[good])
        fair[name] = {"engine_approval": mf_e.by_group.round(4).to_dict(),
                      "traditional_approval": mf_t.by_group.round(4).to_dict(),
                      "engine_parity_gap": round(float(mf_e.difference()), 4),
                      "traditional_parity_gap": round(float(mf_t.difference()), 4),
                      "engine_equal_opportunity_gap": round(float(eo_e.difference()), 4)}
    M["fairness"] = fair

    # 10. stress test, drift, explainability ---------------------------------------------
    fxm = (dec_B.offer_amount > 0) & ((bB.loan_currency == "USD") & (bB.income_currency == "GEL"))
    M["stress_gel_minus20"] = {"fx_mismatch_offers": int(fxm.sum()),
                               "pd_base": round(float(dec_B.pd_offer[fxm].mean()), 4) if fxm.any() else None,
                               "pd_stressed": round(float(dec_B.pd_gel_minus20[fxm].mean()), 4) if fxm.any() else None,
                               "portfolio_pd_base": round(float(dec_B.pd_offer[dec_B.offer_amount > 0].mean()), 4),
                               "portfolio_pd_stressed": round(float(dec_B.pd_gel_minus20[dec_B.offer_amount > 0].mean()), 4)}
    M["drift_psi_A_vs_B"] = {c: round(psi(Xr.loc[iA, c], Xr.loc[iB, c]), 4) for c in RISK_FEATURES}
    sv = eng.explainer.values(Xr[iB].sample(1500, random_state=seed))
    M["shap_importance"] = dict(sorted({c: round(float(v), 4) for c, v in zip(RISK_FEATURES, np.abs(sv).mean(0))}.items(),
                                       key=lambda kv: -kv[1]))

    # 11. latency ------------------------------------------------------------------------
    one = B.iloc[0].to_dict()
    one_tx = tx[tx.borrower_id == one["borrower_id"]].drop(columns=["cat"])
    eng.assess(one, one_tx)                                  # warm-up
    t1 = time.time()
    for _ in range(20):
        eng.assess(one, one_tx)
    M["latency"] = {"single_application_ms": round((time.time() - t1) / 20 * 1000, 1),
                    "batch_applications_per_sec": round(len(B) / batch_sec, 1)}
    M["runtime_sec"] = round(time.time() - t0, 1)

    dec_B.reset_index().to_parquet(REPORTS / "decisions_test.parquet", index=False)
    (REPORTS / "metrics.json").write_text(json.dumps(M, indent=2, ensure_ascii=False, default=float))
    print(json.dumps({k: M[k] for k in ("categoriser", "round_trip_detection", "income", "policy", "latency")},
                     indent=1, default=float)[:6000])
    print(json.dumps({k: M["risk"][k] for k in ("engine", "scorecard", "gbm", "traditional_bureau", "oracle_true_pd", "champion_selection")}, indent=1))
    print("seasonal", M.get("seasonal", {}).get("relative_reduction"), "sanity", M["sanity_counterfactual_max_error"])


if __name__ == "__main__":
    main()
