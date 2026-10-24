"""Income Truth Engine - loan officer & supervisor app (Streamlit).

    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ite import rules  # noqa: E402
from ite.audit import AuditLog  # noqa: E402
from ite.engine import MODEL_VERSION, Engine  # noqa: E402

st.set_page_config(page_title="Income Truth Engine", page_icon="🏦", layout="wide")

NAVY, GREEN, RED, AMBER, GREY = "#16337a", "#1f9d55", "#c53030", "#b7791f", "#8a94a6"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REC_STYLE = {"APPROVE": (GREEN, "Approve"), "APPROVE_REDUCED": (GREEN, "Approve reduced amount"),
             "REVIEW": (AMBER, "Human review required"),
             "REFER": (RED, "Refer to the loan officer: no compliant offer or high risk")}
FIRST_NAMES = ["Giorgi", "Nino", "Davit", "Mariam", "Levan", "Ana", "Irakli", "Tamar", "Luka", "Salome", "Nika", "Eka"]

st.markdown("""
<style>
.block-container{padding-top:1.2rem;max-width:1400px}
.synth{background:#fff6e5;color:#7a4b00;border:1px solid #f0c36d;padding:6px 12px;border-radius:8px;font-size:13px}
.card{border:1px solid rgba(128,128,128,.25);border-radius:12px;padding:14px 16px;height:100%}
.big{font-size:30px;font-weight:800;line-height:1.1}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;color:#fff}
.small{font-size:13px;opacity:.8}
.reason{padding:6px 0;border-bottom:1px solid rgba(128,128,128,.15);font-size:14px}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def load():
    eng = Engine(ROOT / "models")
    bor = pd.read_csv(ROOT / "data" / "borrowers.csv")
    tx = pd.read_parquet(ROOT / "data" / "transactions.parquet")
    dec = pd.read_parquet(ROOT / "reports" / "decisions_test.parquet")
    metrics = json.loads((ROOT / "reports" / "metrics.json").read_text())
    return eng, bor, tx, dec, metrics


eng, bor, tx, dec, M = load()
audit = AuditLog(ROOT / "audit.db")
HIDDEN = [c for c in bor.columns if c.startswith("TRUE_")]
test = bor[bor.cohort == "B"].merge(dec[["borrower_id", "recommendation"]], on="borrower_id")


DEMO_NAMES = {747: "Giorgi", 122: "Levan"}


def persona(bid: int, arch: str) -> str:
    name = DEMO_NAMES.get(bid, FIRST_NAMES[bid % len(FIRST_NAMES)])
    return f"{name} · #{bid} · {arch.replace('_', ' ')}"


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### 🏦 Income Truth Engine")
    st.markdown('<div class="synth">⚠ All applicants and transactions are <b>synthetic</b>.</div>', unsafe_allow_html=True)
    officer = st.text_input("Loan officer ID", "nino.b")
    st.markdown("**Choose an application**")
    demo = {"Giorgi — Kakheti vineyard owner, no credit history": 747,
            "Levan — income inflated by circular transfers": 122}
    pick = st.radio("Demo cases", list(demo) + ["Browse the queue"], index=0)
    if pick == "Browse the queue":
        f_arch = st.multiselect("Employment", sorted(test.archetype.unique()))
        f_rec = st.multiselect("Engine recommendation", sorted(test.recommendation.unique()))
        q = test
        if f_arch:
            q = q[q.archetype.isin(f_arch)]
        if f_rec:
            q = q[q.recommendation.isin(f_rec)]
        bid = st.selectbox("Applicant", q.borrower_id.head(300).tolist(),
                           format_func=lambda i: persona(i, test.set_index("borrower_id").at[i, "archetype"]))
    else:
        bid = demo[pick]
    st.caption(f"Model {MODEL_VERSION} · champion: {eng.risk.champion} · rules {rules.version_for('2026-10-20', eng.cfg)['id']}")

tab_review, tab_results, tab_super, tab_cards = st.tabs(
    ["📝 Loan review", "📊 Portfolio results", "🏛 Supervisor: PTI 2027 simulator", "📄 Model & data cards"])


@st.cache_data(show_spinner=False)
def assess(bid: int) -> dict:
    app = bor[bor.borrower_id == bid].drop(columns=HIDDEN).iloc[0].to_dict()
    t = tx[tx.borrower_id == bid].drop(columns=["category_true", "is_round_trip"])
    return eng.assess(app, t)


# ------------------------------------------------------------------ loan review
with tab_review:
    a = bor[bor.borrower_id == bid].iloc[0]
    r = assess(int(bid))
    color, label = REC_STYLE[r["recommendation"]]
    st.markdown(f"## {persona(int(bid), a.archetype)}")
    st.caption(f"{a.region} · age {a.age} · applied {a.application_date} · consent OB-{int(bid):06d} (read-only, 90 days, purpose: this credit assessment)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="card"><div class="small">Requested</div>
        <div class="big">{a.loan_amount_gel:,.0f} ₾</div>
        <div class="small">{int(a.term_months)} months · {a.loan_currency} · {a.annual_rate:.1%}<br>
        Payment {a.monthly_payment_gel:,.0f} ₾ / month<br>
        Credit bureau: {"<b>no history (thin file)</b>" if a.thin_file else f"score {a.bureau_score:.0f}"}</div></div>""",
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="card"><div class="small">Income: declared vs. estimated from accounts</div>
        <div class="big">{r['inc_q50']:,.0f} ₾</div>
        <div class="small">declared {r['declared_income']:,.0f} ₾ · band {r['inc_q10']:,.0f}–{r['inc_q90']:,.0f} ₾ (P10–P90)<br>
        used for PTI (conservative P25): <b>{r['inc_q25']:,.0f} ₾</b></div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="card"><div class="small">Probability of default (12 m) at offer</div>
        <div class="big" style="color:{color}">{r['pd_offer']:.1%}</div>
        <div class="small">at requested amount: {r['pd_requested']:.1%}<br>GEL −20% stress: {r['pd_gel_minus20']:.1%}</div></div>""",
                    unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="card"><div class="small">Engine recommendation</div>
        <div style="margin:6px 0"><span class="pill" style="background:{color}">{label}</span></div>
        <div class="big">{r['offer']['amount']:,.0f} ₾</div>
        <div class="small">{r['offer']['term_months']} months · {r['offer']['monthly_payment']:,.0f} ₾ / month</div></div>""",
                    unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Income seen in the accounts, by month")
        prof = r["seasonal_schedule"]["income_profile_by_month"] if r["seasonal_schedule"] else None
        t = tx[(tx.borrower_id == bid)].copy()
        t["date"] = pd.to_datetime(t["date"])
        t["gel"] = np.where(t.currency == "USD", t.amount * 2.70, t.amount)
        cats = {"salary": "Salary", "harvest": "Harvest sales", "p2p_in": "Client / P2P transfers", "remittance": "Remittances (USD)"}
        fig = go.Figure()
        pal = {"Salary": NAVY, "Harvest sales": GREEN, "Client / P2P transfers": "#5b8def", "Remittances (USD)": AMBER}
        tc = eng.cat_model
        from ite import categorise
        t["cat"] = categorise.predict(tc, t.drop(columns=["category_true", "is_round_trip"]))
        inc = t[t.cat.isin(cats) & (t.gel > 0)]
        inc = inc.assign(month=inc.date.dt.to_period("M").astype(str), kind=inc.cat.map(cats))
        g = inc.groupby(["month", "kind"]).gel.sum().reset_index()
        for k in cats.values():
            gg = g[g.kind == k]
            if len(gg):
                fig.add_bar(x=gg.month, y=gg.gel, name=k, marker_color=pal[k])
        fig.add_hline(y=r["declared_income"], line_dash="dot", line_color=RED, annotation_text="declared",
                      annotation_position="top left")
        fig.add_hline(y=r["inc_q50"], line_dash="dash", line_color=GREEN, annotation_text="engine estimate (P50)",
                      annotation_position="bottom left")
        fig.update_layout(barmode="stack", height=320, margin=dict(l=10, r=10, t=10, b=10),
                          legend=dict(orientation="h", y=-0.2), yaxis_title="GEL")
        st.plotly_chart(fig, width="stretch")
        st.caption("Own-account transfers, one-off inflows and circular transfers are excluded. "
                   "The estimate also accounts for income the bank cannot see (cash, other banks), with an uncertainty band.")

        st.markdown("#### Why: main factors (champion model)")
        for x in r["reasons"]:
            arrow = "🔺" if x["impact"] > 0 else "🟢"
            st.markdown(f"<div class='reason'>{arrow} <b>{x['en']}</b><br><span class='small'>{x['ka']}</span></div>",
                        unsafe_allow_html=True)

    with right:
        st.markdown("#### NBG responsible-lending checks")
        rows = [("PTI at requested amount", f"{r['pti_requested']:.0%} vs limit {r['pti_limit']:.0%}", r["pti_pass"])]
        if r.get("ltv") is not None and not pd.isna(r["ltv"]):
            rows.append(("LTV", f"{r['ltv']:.0%} vs limit {r['ltv_limit']:.0%}", bool(r["ltv_pass"])))
        else:
            rows.append(("LTV", "no collateral", True))
        rows.append(("Currency", f"{a.loan_currency} loan, income in {a.income_currency}",
                     a.loan_currency == "GEL" or a.loan_currency == a.income_currency))
        rows.append(("Max compliant amount", f"{r['max_compliant_amount']:,.0f} ₾ for {int(a.term_months)} m", True))
        for name, val, ok in rows:
            st.markdown(f"{'✅' if ok else '❌'} **{name}** — {val}")
        st.caption(f"Rules version {r['rules_version']} (versioned config; 2027 thresholds pre-loaded).")

        if r["flags"]:
            st.markdown("#### Flags for the officer")
            for f in r["flags"]:
                st.warning(f)

        st.markdown("#### Path to yes")
        alt = pd.DataFrame(r["alternatives"])
        alt["meets request"] = alt.max_amount >= a.loan_amount_gel
        st.dataframe(alt.rename(columns={"term_months": "Term (months)", "max_amount": "Max compliant amount (₾)"}),
                     hide_index=True, width="stretch")
        if r["seasonal_schedule"]:
            s = r["seasonal_schedule"]
            st.markdown("**Harvest-shaped repayment option** (same present value as the annuity)")
            mlab = [MONTHS[(s["start_month"] - 1 + i) % 12] for i in range(12)]
            f2 = go.Figure()
            f2.add_bar(x=mlab, y=s["payments_first_12"], name="Seasonal payment", marker_color=GREEN)
            f2.add_scatter(x=mlab, y=[s["annuity_payment"]] * 12, name="Equal annuity", line=dict(color=RED, dash="dash"))
            f2.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.3),
                             yaxis_title="GEL")
            st.plotly_chart(f2, width="stretch")
            st.caption(s["note"])

    st.divider()
    st.markdown("### Officer decision")
    d1, d2 = st.columns([1, 1])
    with d1:
        options = ["APPROVE_REDUCED" if r["offer"]["amount"] < a.loan_amount_gel else "APPROVE", "APPROVE_SEASONAL",
                   "REQUEST_DOCUMENTS", "REJECT"]
        if not r["seasonal_schedule"]:
            options.remove("APPROVE_SEASONAL")
        choice = st.radio("Decision", options, horizontal=True)
        amount = st.number_input("Amount (₾)", 0.0, float(a.loan_amount_gel), float(r["offer"]["amount"]), 100.0)
        overriding = choice.split("_")[0] != r["recommendation"].split("_")[0] or amount > r["max_compliant_amount"]
        reason = st.text_area("Override reason (required when you disagree with the engine)", disabled=not overriding)
        if amount > r["max_compliant_amount"]:
            st.error("This amount breaks the NBG PTI/LTV limit. The engine will not record it.")
        if st.button("Record decision", type="primary", disabled=amount > r["max_compliant_amount"] and choice.startswith("APPROVE")):
            if overriding and len(reason.strip()) < 10:
                st.error("Please give a reason (10+ characters) for overriding the engine.")
            else:
                h = audit.append({"borrower_id": int(bid), "officer_id": officer, "decision": choice, "amount_gel": amount,
                                  "engine_recommendation": r["recommendation"], "override": overriding,
                                  "override_reason": reason if overriding else None, "pd_offer": r["pd_offer"],
                                  "rules_version": r["rules_version"], "model_version": MODEL_VERSION})
                st.success(f"Recorded. Audit hash {h[:16]}…")
    with d2:
        lang = st.radio("Letter to the applicant", ["ქართული", "English"], horizontal=True)
        st.text_area("Generated from the decision record only (no free-form AI text)",
                     r["letter_ka"] if lang == "ქართული" else r["letter_en"], height=200)
    ok, n = audit.verify()
    st.caption(f"Audit log: {n} records · hash chain {'intact ✅' if ok else 'BROKEN ❌'}")
    recs = audit.records(5)
    if recs:
        st.dataframe(pd.DataFrame(recs)[["seq", "ts", "officer_id", "borrower_id", "decision", "amount_gel",
                                         "engine_recommendation", "override", "hash"]], hide_index=True,
                     width="stretch")

# ------------------------------------------------------------------ portfolio results
with tab_results:
    P, R, I = M["policy"], M["risk"], M["income"]
    st.markdown(f"### Out-of-time test: {len(dec):,} synthetic applications from July 2026 (model trained on July 2025)")
    k = st.columns(5)
    k[0].metric("Approval rate", f"{P['engine_auto']['approval_rate']:.0%}",
                f"{(P['engine_auto']['approval_rate'] - P['traditional']['approval_rate']) * 100:+.0f} pp vs traditional")
    k[1].metric("Expected bad rate", f"{P['engine_auto']['expected_bad_rate']:.1%}",
                f"{(P['engine_auto']['expected_bad_rate'] - P['traditional']['expected_bad_rate']) * 100:+.1f} pp", delta_color="inverse")
    k[2].metric("Thin-file applicants approved", f"{P['engine_auto']['thin_file_approved']:,}", "traditional: 0")
    k[3].metric("Income error (median)", f"{I['mdape_engine_p50']:.1%}", f"declared: {I['mdape_declared']:.1%}", delta_color="off")
    k[4].metric("AUC thin-file", f"{R['thin_file']['engine']['auc']:.3f}", f"bureau model: {R['thin_file']['traditional_bureau']['auc']:.3f}", delta_color="off")
    c1, c2 = st.columns(2)
    with c1:
        f = go.Figure()
        for name, col, lab in (("engine", GREEN, "Income Truth Engine"), ("traditional", RED, "Traditional (bureau + declared income)")):
            cv = pd.DataFrame(P["curves"][name])
            f.add_scatter(x=cv.approval_rate, y=cv.bad_rate, mode="lines+markers", name=lab, line=dict(color=col))
        f.update_layout(title="More approvals at every bad rate", xaxis_title="Approval rate", yaxis_title="Expected bad rate",
                        xaxis_tickformat=".0%", yaxis_tickformat=".1%", height=360, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(f, width="stretch")
    with c2:
        ba = pd.DataFrame(I["by_archetype"]).T
        f = go.Figure()
        f.add_bar(x=ba.index, y=ba.declared, name="Declared income", marker_color=RED)
        f.add_bar(x=ba.index, y=ba.naive_inflows, name="Sum of inflows", marker_color=GREY)
        f.add_bar(x=ba.index, y=ba.engine_p50, name="Engine estimate", marker_color=GREEN)
        f.update_layout(title="Median income error by borrower type", yaxis_tickformat=".0%", height=360,
                        legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(f, width="stretch")
    st.markdown("#### Policy comparison")
    tbl = pd.DataFrame([P["traditional"], P["engine_auto"], P["engine_matched"]]).set_index("policy")
    st.dataframe(tbl.style.format({"approval_rate": "{:.1%}", "thin_file_approval_rate": "{:.1%}", "expected_bad_rate": "{:.2%}",
                                   "volume_gel": "{:,.0f}", "expected_loss_gel": "{:,.0f}", "loss_rate": "{:.2%}",
                                   "pd_threshold": "{:.3f}"}), width="stretch")
    st.caption("Expected bad rate = ground-truth default probability of each approved offer (known because the data is synthetic). "
               "Hidden PTI breaches = approvals that break the NBG PTI limit on the borrower's TRUE income.")

# ------------------------------------------------------------------ supervisor
with tab_super:
    st.markdown("### Impact of NBG's 2027 PTI threshold changes on this application pool")
    st.caption("The 25% PTI limit currently applies below 1,500 ₾ monthly income; it extends to 2,000 ₾ from 1 Feb 2027 "
               "and 2,500 ₾ from 1 Sep 2027. Computed with the same rules engine on engine income estimates.")
    d = dec.merge(bor[["borrower_id", "region", "archetype"]], on="borrower_id")
    res = []
    for as_of in ("2026-10-20", "2027-02-01", "2027-09-01"):
        c = rules.check(d.inc_q25, d.existing_debt, 0, 0, d.loan_currency, d.income_currency, d.annual_rate,
                        d.term_months, None, as_of, eng.cfg)
        d[f"max_{as_of}"] = np.minimum(d.requested_amount, np.floor(c["max_amount"] / 100) * 100)
        res.append({"rules": c["rules_version"], "as_of": as_of, "affordable_credit_gel": d[f"max_{as_of}"].sum()})
    rs = pd.DataFrame(res)
    base = rs.affordable_credit_gel.iloc[0]
    cc = st.columns(3)
    for i, row in rs.iterrows():
        cc[i].metric(f"Rules {row.rules}", f"{row.affordable_credit_gel / 1e6:,.1f} M ₾",
                     None if i == 0 else f"{(row.affordable_credit_gel / base - 1) * 100:+.1f}%", delta_color="inverse")
    d["cut_2027_09"] = 1 - d["max_2027-09-01"] / d["max_2026-10-20"].replace(0, np.nan)
    hit = d.assign(affected=d["max_2027-09-01"] < d["max_2026-10-20"])
    g = hit.groupby("region").agg(applicants=("borrower_id", "size"), affected=("affected", "mean"),
                                  credit_cut=("cut_2027_09", "mean")).reset_index()
    f = go.Figure()
    f.add_bar(x=g.region, y=g.affected, marker_color=NAVY, text=[f"{v:.0%}" for v in g.affected], textposition="outside")
    f.update_layout(title="Share of applicants whose maximum compliant loan falls by Sep 2027", yaxis_tickformat=".0%", height=360)
    st.plotly_chart(f, width="stretch")
    st.dataframe(g.style.format({"affected": "{:.1%}", "credit_cut": "{:.1%}"}), hide_index=True)

# ------------------------------------------------------------------ cards
with tab_cards:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown((ROOT / "docs" / "MODEL_CARD.md").read_text() if (ROOT / "docs" / "MODEL_CARD.md").exists() else "Model card missing")
    with c2:
        st.markdown((ROOT / "docs" / "DATA_CARD.md").read_text() if (ROOT / "docs" / "DATA_CARD.md").exists() else "Data card missing")
