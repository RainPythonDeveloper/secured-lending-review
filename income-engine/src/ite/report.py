"""Build the results page (reports/results.html), PNG charts for slides, and the model & data cards.

    python -m ite.report
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from . import rules

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REP, FIG, DOCS = ROOT / "reports", ROOT / "reports" / "figures", ROOT / "docs"
ARCH_LABEL = {"salaried_tbilisi": "Salaried (Tbilisi)", "farmer_kakheti": "Farmers (Kakheti)",
              "self_employed": "Self-employed", "remittance_hh": "Remittance households",
              "young_first_loan": "Young first-time"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# --------------------------------------------------------------------------- SVG helpers
def _nice(v):
    return f"{v:.0%}" if v >= 0.1 or v == 0 else f"{v:.1%}"


def svg_lines(series, xlab, ylab, xmax=1.0, ymax=None, w=640, h=340, pct=True, diag=False, xticks=None, yticks=None):
    """series: list of (label, css-var color, xs, ys, dashed)."""
    L, R, T, B = 56, 16, 16, 44
    ymax = ymax or max(max(s[3]) for s in series) * 1.15
    X = lambda x: L + (x / xmax) * (w - L - R)
    Y = lambda y: T + (1 - y / ymax) * (h - T - B)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    yticks = yticks or list(np.linspace(0, ymax, 5))
    for t in yticks:
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>'
                   f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{_nice(t) if pct else f"{t:.2f}"}</text>')
    for t in (xticks or list(np.linspace(0, xmax, 6))):
        out.append(f'<text x="{X(t):.1f}" y="{h - B + 18}" class="tick" text-anchor="middle">{_nice(t) if pct else f"{t:.1f}"}</text>')
    if diag:
        out.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(xmax)}" y2="{Y(min(ymax, xmax))}" class="diag"/>')
    for lab, col, xs, ys, dashed in series:
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in zip(xs, ys))
        out.append(f'<polyline points="{pts}" fill="none" stroke="var({col})" stroke-width="2.5" '
                   f'{"stroke-dasharray=\"6 5\"" if dashed else ""} stroke-linejoin="round"/>')
        if len(xs) < 30:
            out += [f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3" fill="var({col})"/>' for x, y in zip(xs, ys)]
    out.append(f'<text x="{(L + w - R) / 2}" y="{h - 6}" class="axis" text-anchor="middle">{xlab}</text>'
               f'<text x="14" y="{(T + h - B) / 2}" class="axis" text-anchor="middle" transform="rotate(-90 14 {(T + h - B) / 2})">{ylab}</text>')
    out.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:var({c})"></i>{escape(l)}</span>' for l, c, *_ in series)
    return "".join(out) + f'<div class="legend">{legend}</div>'


def svg_bars(cats, groups, w=640, h=320, pct=True, ymax=None, label_fmt=None):
    """groups: list of (label, css-var color, values)."""
    L, R, T, B = 48, 12, 22, 58
    vals = [v for g in groups for v in g[2]]
    ymax = ymax or max(vals) * 1.2
    n, k = len(cats), len(groups)
    band = (w - L - R) / n
    bw = min(34, band * 0.8 / k)
    Y = lambda y: T + (1 - y / ymax) * (h - T - B)
    fmt = label_fmt or (_nice if pct else (lambda v: f"{v:,.0f}"))
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    for t in np.linspace(0, ymax, 5):
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>'
                   f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" class="tick" text-anchor="end">{fmt(t)}</text>')
    for i, c in enumerate(cats):
        x0 = L + i * band + (band - bw * k) / 2
        for j, (_, col, v) in enumerate(groups):
            x = x0 + j * bw
            out.append(f'<rect x="{x:.1f}" y="{Y(v[i]):.1f}" width="{bw - 3:.1f}" height="{Y(0) - Y(v[i]):.1f}" rx="2" fill="var({col})"/>')
            if k <= 3:
                out.append(f'<text x="{x + (bw - 3) / 2:.1f}" y="{Y(v[i]) - 5:.1f}" class="val" text-anchor="middle">{fmt(v[i])}</text>')
        words = c.split(" ")
        lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else [c]
        for li, ln in enumerate(lines):
            out.append(f'<text x="{L + i * band + band / 2:.1f}" y="{h - B + 18 + li * 14}" class="tick" text-anchor="middle">{escape(ln)}</text>')
    out.append("</svg>")
    legend = "".join(f'<span class="lg"><i style="background:var({c})"></i>{escape(l)}</span>' for l, c, _ in groups)
    return "".join(out) + f'<div class="legend">{legend}</div>'


# --------------------------------------------------------------------------- PNGs for slides
def pngs(M, sup):
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})
    G, T, W = "#2f7d4f", "#8a94a6", "#8c2f45"
    P = M["policy"]["curves"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, c, lab in (("engine", G, "Income Truth Engine"), ("traditional", T, "Traditional (bureau + declared income)")):
        d = pd.DataFrame(P[k])
        ax.plot(d.approval_rate, d.bad_rate, "-o", color=c, label=lab, ms=4, lw=2.5)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=1))
    ax.set_xlabel("Approval rate"); ax.set_ylabel("Expected bad rate"); ax.legend(frameon=False)
    ax.set_title("More approvals at every level of risk", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "approval_vs_bad_rate.png", dpi=200); plt.close(fig)

    ba = pd.DataFrame(M["income"]["by_archetype"]).T
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(ba)); wdt = 0.27
    for i, (col, c, lab) in enumerate((("declared", W, "Declared income"), ("naive_inflows", T, "Sum of inflows"),
                                       ("engine_p50", G, "Engine estimate"))):
        ax.bar(x + (i - 1) * wdt, ba[col], wdt, color=c, label=lab)
    ax.set_xticks(x, [ARCH_LABEL[a] for a in ba.index], rotation=12)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_ylabel("Median income error"); ax.legend(frameon=False)
    ax.set_title("Income error by borrower type", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "income_error.png", dpi=200); plt.close(fig)

    R = M["risk"]["roc"]
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for k, c, lab in (("engine", G, f"Engine (AUC {M['risk']['engine']['auc']:.3f})"),
                      ("traditional_bureau", T, f"Bureau model (AUC {M['risk']['traditional_bureau']['auc']:.3f})")):
        ax.plot(R[k]["fpr"], R[k]["tpr"], color=c, lw=2.5, label=lab)
    ax.plot([0, 1], [0, 1], ":", color="#bbb"); ax.legend(frameon=False, loc="lower right")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("Out-of-time ROC", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "roc.png", dpi=200); plt.close(fig)

    s = M["seasonal"]["example"]
    lab = [MONTHS[(s["start_month"] - 1 + i) % 12] for i in range(12)]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(lab, s["seasonal"], color=G, label="Harvest-shaped payment")
    ax.plot(lab, s["annuity"], "--", color=W, lw=2, label="Equal annuity")
    ax.set_ylabel("GEL per month"); ax.legend(frameon=False)
    ax.set_title(f"Harvest-shaped repayment: default risk {M['seasonal']['relative_reduction']:.0%} lower",
                 loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "seasonal_schedule.png", dpi=200); plt.close(fig)

    fr = M["fairness"]["region"]
    reg = list(fr["engine_approval"])
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(reg))
    ax.bar(x - 0.2, [fr["traditional_approval"][r] for r in reg], 0.4, color=T, label="Traditional")
    ax.bar(x + 0.2, [fr["engine_approval"][r] for r in reg], 0.4, color=G, label="Engine (same bad rate)")
    ax.set_xticks(x, reg); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_ylabel("Approval rate"); ax.legend(frameon=False)
    ax.set_title("Approval rate by region", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "fairness_region.png", dpi=200); plt.close(fig)


# --------------------------------------------------------------------------- supervisor simulation
def supervisor(cfg):
    d = pd.read_parquet(REP / "decisions_test.parquet")
    b = pd.read_csv(ROOT / "data" / "borrowers.csv")[["borrower_id", "region", "archetype"]]
    d = d.merge(b, on="borrower_id")
    out = {}
    for as_of in ("2026-10-20", "2027-02-01", "2027-09-01"):
        c = rules.check(d.inc_q25, d.existing_debt, 0, 0, d.loan_currency, d.income_currency, d.annual_rate,
                        d.term_months, None, as_of, cfg)
        d[as_of] = np.minimum(d.requested_amount, np.floor(c["max_amount"] / 100) * 100)
        out[as_of] = {"rules": c["rules_version"], "credit": float(d[as_of].sum())}
    d["hit"] = d["2027-09-01"] < d["2026-10-20"]
    by = d.groupby("region").hit.mean().round(4).to_dict()
    return {"versions": out, "affected_share": round(float(d.hit.mean()), 4), "affected_by_region": by,
            "credit_change": round(out["2027-09-01"]["credit"] / out["2026-10-20"]["credit"] - 1, 4)}


# --------------------------------------------------------------------------- cards
def cards(M):
    D, R, I = M["data"], M["risk"], M["income"]
    DOCS.mkdir(exist_ok=True)
    (DOCS / "DATA_CARD.md").write_text(f"""# Data card

**Status:** 100% synthetic. No real person, account or bank is represented.
Generator `src/ite/synth.py` v{D['generator_version']}, seed {D['seed']}; rerun to reproduce exactly.

| | |
|---|---|
| Borrowers | {D['n_borrowers']:,} (cohort A: applications Jul 2025, cohort B: Jul 2026) |
| Transactions | {D['n_transactions']:,} over {D['observation_months']} months before each application |
| Default rate (12 months) | {D['default_rate']:.1%} (A {D['default_rate_by_cohort']['A']:.1%}, B {D['default_rate_by_cohort']['B']:.1%}) |
| Thin-file share | {D['thin_file_share']:.1%} |
| Income-faking (round-trip) share | {D['round_trip_share']:.1%} |

**Borrower types:** salaried (Tbilisi), farmers (Kakheti, Aug–Oct harvest), self-employed (Imereti),
remittance households (Samegrelo, USD inflows), young first-time borrowers.

**Realism built in:** cash income and income at other banks that the model cannot see; own-account
transfers; one-off inflows; generic or mixed Georgian/Latin transaction descriptions; circular
transfers used to fake income (some returned through a different account, some legitimate refunds
that look the same); a latent "fragility" trait and post-application shocks that no feature captures;
drift between cohorts (higher rates, slightly higher default rate in 2026).

**Default mechanism (hidden ground truth):** `{D['pd_mechanism']}`

**Columns never given to any model:** every `TRUE_*` column, `category_true` (used only to train the
transaction categoriser, standing in for a bank's labelled history) and `is_round_trip`.

**Calibrate before real use:** {", ".join(D['calibration_sources_to_replace'])}.
""")
    sc = "\n".join(f"| {f} | {v['expected']} | {v['coef']:+.3f} | {'in model' if v['in_model'] else 'dropped'} |"
                   for f, v in R["sign_checks"].items())
    dropped = ", ".join(f"`{d['feature']}`" for d in R["scorecard_dropped_features"]) or "none"
    drift = sorted(M["drift_psi_A_vs_B"].items(), key=lambda kv: -kv[1])[:3]
    (DOCS / "MODEL_CARD.md").write_text(f"""# Model card: Income Truth Engine {M['model_version']}

**Purpose.** Help a loan officer at a bank or microfinance institution assess retail applicants,
especially thin-file borrowers, from consented account data: estimate real income with an
uncertainty band, apply NBG PTI/LTV limits, estimate 12-month default risk, explain it, and suggest
a compliant offer. **The officer makes every final decision.**

**Not for:** fully automated decisions, business loans, collateral valuation, or any use on real
customers before validation on real data in a sandbox.

## Components
| Step | Method |
|---|---|
| Transaction categoriser | Character n-gram TF-IDF + logistic regression (works on Georgian script) |
| Circular-transfer detection | Inflow returned to the same counterparty within 7 days (rule) |
| Income estimate | LightGBM quantile regression (P10/P25/P50/P90), split-conformal calibrated |
| NBG rules | Versioned YAML config, dated versions incl. 2027 thresholds |
| Risk (champion) | **{R['champion_selection']['champion']}** chosen over the alternative on validation AUC ({R['champion_selection']} ) |
| Explanations | Exact per-feature contributions (scorecard) or SHAP (GBM), in Georgian and English |

## Out-of-time performance (cohort B, July 2026)
| Model | AUC | Gini | KS | Brier |
|---|---|---|---|---|
| Engine (champion) | {R['engine']['auc']:.3f} | {R['engine']['gini']:.3f} | {R['engine']['ks']:.3f} | {R['engine']['brier']:.4f} |
| Gradient boosting (challenger) | {R['gbm']['auc']:.3f} | {R['gbm']['gini']:.3f} | {R['gbm']['ks']:.3f} | {R['gbm']['brier']:.4f} |
| Traditional bureau model | {R['traditional_bureau']['auc']:.3f} | {R['traditional_bureau']['gini']:.3f} | {R['traditional_bureau']['ks']:.3f} | {R['traditional_bureau']['brier']:.4f} |
| Theoretical ceiling (true PD) | {R['oracle_true_pd']['auc']:.3f} | {R['oracle_true_pd']['gini']:.3f} | | |

Thin-file applicants: engine AUC {R['thin_file']['engine']['auc']:.3f} vs bureau model {R['thin_file']['traditional_bureau']['auc']:.3f}.
The engine reaches {R['share_of_oracle_gini']:.0%} of the theoretical maximum Gini.

Income: median error {I['mdape_engine_p50']:.1%} vs {I['mdape_declared']:.1%} for declared income;
P10–P90 band covers the true income {I['band_coverage_p10_p90']:.0%} of the time (target 80%).

## Model-risk controls
- Champion–challenger: the simpler model is kept unless the complex one gains more than {R['champion_selection']['min_gain_required']} AUC.
- Business-logic sign checks (scorecard). Features with counter-intuitive signs are dropped automatically: {dropped}.

| Feature | Expected | Coefficient | Status |
|---|---|---|---|
{sc}

- Monotone constraints on the GBM challenger for debt burden, betting, late bills, savings, bureau score.
- Gender, age and region are **not** model inputs; they are used only for fairness monitoring.
- Drift monitoring (PSI, A→B): highest {", ".join(f"{k} {v:.2f}" for k, v in drift)}. PSI above 0.1 triggers review
  (here `annual_rate` drifts because rates rose; the engine flags it as designed).
- Stress test: lari −20% re-scores every USD loan to a GEL earner.
- Tamper-evident audit log (hash chain) of every officer decision and override.

## Known limitations
- Trained and tested on synthetic data; performance on real data is unknown until a sandbox pilot.
- Income model training needs verified income labels (payroll, Revenue Service data or documents).
- Banks only observe outcomes for approved loans (selection bias); real deployment needs reject inference.
- Circular-transfer detection misses transfers returned through a different account.
- How NBG's PTI rule applies to non-equal (harvest-shaped) schedules must be confirmed with NBG.
""")


# --------------------------------------------------------------------------- HTML page
def page(M, sup):
    P, R, I, F = M["policy"], M["risk"], M["income"], M["fairness"]
    tr, en, em = P["traditional"], P["engine_auto"], P["engine_matched"]
    curve = svg_lines([
        ("Income Truth Engine", "--eng", [c["approval_rate"] for c in P["curves"]["engine"]],
         [c["bad_rate"] for c in P["curves"]["engine"]], False),
        ("Traditional: bureau score + declared income", "--trad", [c["approval_rate"] for c in P["curves"]["traditional"]],
         [c["bad_rate"] for c in P["curves"]["traditional"]], True)],
        "Approval rate", "Expected bad rate", xmax=1.0, ymax=0.08, yticks=[0, .02, .04, .06, .08])
    ba = pd.DataFrame(I["by_archetype"]).T
    inc_chart = svg_bars([ARCH_LABEL[a] for a in ba.index], [
        ("Declared income", "--warn", ba.declared.tolist()), ("Sum of all inflows", "--trad", ba.naive_inflows.tolist()),
        ("Engine estimate (P50)", "--eng", ba.engine_p50.tolist())], ymax=0.3)
    roc = svg_lines([
        (f"Engine, AUC {R['engine']['auc']:.3f}", "--eng", R["roc"]["engine"]["fpr"], R["roc"]["engine"]["tpr"], False),
        (f"Gradient boosting, AUC {R['gbm']['auc']:.3f}", "--ink2", R["roc"]["gbm"]["fpr"], R["roc"]["gbm"]["tpr"], True),
        (f"Bureau model, AUC {R['traditional_bureau']['auc']:.3f}", "--trad", R["roc"]["traditional_bureau"]["fpr"],
         R["roc"]["traditional_bureau"]["tpr"], True)],
        "False positive rate", "True positive rate", xmax=1.0, ymax=1.0, diag=True, w=520, h=360,
        yticks=[0, .25, .5, .75, 1], xticks=[0, .25, .5, .75, 1])
    cal = R["calibration"]
    calib = svg_lines([("Engine (out-of-time deciles)", "--eng", [c["predicted"] for c in cal], [c["observed"] for c in cal], False)],
                      "Predicted PD", "Observed default rate", xmax=0.5, ymax=0.5, diag=True, w=520, h=360,
                      yticks=[0, .1, .2, .3, .4, .5], xticks=[0, .1, .2, .3, .4, .5])
    s = M["seasonal"]["example"]
    mlab = [MONTHS[(s["start_month"] - 1 + i) % 12] for i in range(12)]
    seas = svg_bars(mlab, [("Harvest-shaped payment", "--eng", s["seasonal"]), ("Equal annuity", "--warn", s["annuity"])],
                    pct=False, w=640, h=280)
    fr = F["region"]
    regs = list(fr["engine_approval"])
    fair_r = svg_bars(regs, [("Traditional", "--trad", [fr["traditional_approval"][r] for r in regs]),
                             ("Engine at the same bad rate", "--eng", [fr["engine_approval"][r] for r in regs])], ymax=1.05)
    fa = F["age_band"]
    ages = list(fa["engine_approval"])
    fair_a = svg_bars(ages, [("Traditional", "--trad", [fa["traditional_approval"][r] for r in ages]),
                             ("Engine at the same bad rate", "--eng", [fa["engine_approval"][r] for r in ages])], ymax=1.05)
    sv = sup["versions"]
    sup_regs = list(sup["affected_by_region"])
    sup_chart = svg_bars(sup_regs, [("Applicants whose maximum compliant loan falls by Sep 2027", "--ink2",
                                     [sup["affected_by_region"][r] for r in sup_regs])], ymax=max(sup["affected_by_region"].values()) * 1.3 + 0.01)
    rt = I["round_trippers"]
    signs = "".join(f"<tr><td>{escape(f)}</td><td>{v['expected']}</td><td class='num'>{v['coef']:+.3f}</td>"
                    f"<td>{'<span class=\"chip ok\">in model</span>' if v['in_model'] else '<span class=\"chip mute\">dropped</span>'}</td></tr>"
                    for f, v in R["sign_checks"].items())
    psi = sorted(M["drift_psi_A_vs_B"].items(), key=lambda kv: -kv[1])[:5]
    psi_rows = "".join(f"<tr><td>{escape(k)}</td><td class='num'>{v:.3f}</td><td>{'<span class=\"chip warn\">review</span>' if v > 0.1 else '<span class=\"chip ok\">stable</span>'}</td></tr>" for k, v in psi)

    def prow(p, name):
        return (f"<tr><th scope='row'>{name}</th><td class='num'>{p['approval_rate']:.1%}</td><td class='num'>{p['thin_file_approved']:,}</td>"
                f"<td class='num'>{p['expected_bad_rate']:.2%}</td><td class='num'>{p['loss_rate']:.2%}</td>"
                f"<td class='num'>{p['volume_gel'] / 1e6:,.1f} M</td><td class='num'>{p['hidden_pti_breaches']}</td>"
                f"<td class='num'>{p['round_trippers_approved']}</td></tr>")

    n_test = int(sum(c["n"] for c in R["calibration"]))
    css = """
<title>Income Truth Engine Results</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a single reading column of evidence sections; each section = claim, chart, numbers. */
:root{
  --bg:#f5f7f6; --surface:#ffffff; --ink:#15212b; --ink2:#3d5a80; --muted:#5d6b75; --line:#dde3e1;
  --eng:#2f7d4f; --trad:#9aa4ad; --warn:#9b3348; --amber:#a86a12; --chipbg:#e8efe9;
  --f-display:"Bricolage Grotesque", "Segoe UI", system-ui, sans-serif;
  --f-body:"IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --f-mono:"IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f1517; --surface:#161f22; --ink:#e6ecea; --ink2:#8fb3df; --muted:#9aa8ae; --line:#27353a;
  --eng:#5fc08a; --trad:#6b7780; --warn:#e07a8f; --amber:#e3a94b; --chipbg:#1e2d27; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f1517; --surface:#161f22; --ink:#e6ecea; --ink2:#8fb3df; --muted:#9aa8ae; --line:#27353a;
  --eng:#5fc08a; --trad:#6b7780; --warn:#e07a8f; --amber:#e3a94b; --chipbg:#1e2d27; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.6 var(--f-body);margin:0}
.wrap{max-width:980px;margin:0 auto;padding-block:40px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1,h2,h3{font-family:var(--f-display);text-wrap:balance;line-height:1.15;margin:0}
h1{font-size:clamp(32px,6vw,54px);font-weight:800;letter-spacing:-.02em}
h2{font-size:clamp(22px,3.4vw,30px);font-weight:800;margin-bottom:6px}
h3{font-size:17px;font-weight:600;font-family:var(--f-body)}
p{margin:0;max-width:68ch}
.eyebrow{font:500 12px/1 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--eng)}
.lede{font-size:18px;color:var(--muted);margin-top:12px}
.synth{display:inline-flex;gap:8px;align-items:center;margin-top:16px;font:500 13px var(--f-mono);color:var(--amber);border:1px solid var(--amber);padding:4px 10px;border-radius:6px}
header{display:grid;gap:4px;padding-bottom:28px;border-bottom:1px solid var(--line)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:28px 0 8px}
.kpi{background:var(--surface);padding:16px;display:grid;gap:2px;min-width:0}
.kpi b{font:800 30px/1.1 var(--f-display);color:var(--ink);font-variant-numeric:tabular-nums}
.kpi span{font-size:13px;color:var(--muted)}
.kpi em{font:500 12px var(--f-mono);font-style:normal;color:var(--eng)}
section{display:grid;gap:14px;padding-top:44px}
.fig{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0;overflow-x:auto}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--line);stroke-width:1}
.chart .diag{stroke:var(--trad);stroke-dasharray:3 4}
.chart .tick{fill:var(--muted);font:11px var(--f-mono)}
.chart .axis{fill:var(--muted);font:12px var(--f-body)}
.chart .val{fill:var(--ink);font:500 10.5px var(--f-mono)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--muted);margin-top:6px}
.lg{display:inline-flex;align-items:center;gap:6px}.lg i{width:12px;height:12px;border-radius:2px;display:inline-block}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
thead th{font:500 11px var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}
.num{font-family:var(--f-mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
tr.hl th,tr.hl td{background:var(--chipbg)}
.chip{font:500 11px var(--f-mono);padding:2px 8px;border-radius:999px;background:var(--chipbg);color:var(--eng)}
.chip.warn{color:var(--amber)}.chip.mute{color:var(--muted);background:transparent;border:1px solid var(--line)}
.note{font-size:13px;color:var(--muted)}
ul.plain{margin:0;padding-left:18px;display:grid;gap:6px;max-width:72ch}
footer{margin-top:56px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
</style>"""
    html = f"""{css}
<div class="wrap">
<header>
  <span class="eyebrow">AI in Finance · Credit Risk &amp; Lending · Fintech Hackathon 2026</span>
  <h1>Income Truth Engine</h1>
  <p class="lede">Lending to Georgians the bureau can't see. The engine reads consented bank transactions, estimates real
  income with an uncertainty band, applies NBG PTI and LTV limits, explains the risk in Georgian and English, and leaves
  the decision to a loan officer.</p>
  <span class="synth">⚠ Synthetic data · trained on July 2025 applications · tested out-of-time on {n_test:,} July 2026 applications</span>
</header>

<div class="kpis">
  <div class="kpi"><b>{en['approval_rate']:.0%}</b><span>applicants approved (traditional {tr['approval_rate']:.0%})</span><em>+{(en['approval_rate'] - tr['approval_rate']) * 100:.0f} pp</em></div>
  <div class="kpi"><b>{en['expected_bad_rate']:.1%}</b><span>expected bad rate (traditional {tr['expected_bad_rate']:.1%})</span><em>lower risk on more loans</em></div>
  <div class="kpi"><b>{en['thin_file_approved']:,}</b><span>thin-file applicants approved (traditional 0)</span><em>no bureau history needed</em></div>
  <div class="kpi"><b>{I['mdape_engine_p50']:.1%}</b><span>median income error (declared {I['mdape_declared']:.1%})</span><em>{1 - I['mdape_engine_p50'] / I['mdape_declared']:.0%} smaller error</em></div>
  <div class="kpi"><b>{en['round_trippers_approved']}</b><span>income-fakers auto-approved (traditional {tr['round_trippers_approved']})</span><em>circular transfers flagged</em></div>
</div>
<p class="note">Bad rates are each approved offer's true default probability, which is known because the data is synthetic.
"Traditional" approves applicants with a bureau score of 600+ and caps the amount at the NBG PTI limit on declared income.</p>

<section>
  <span class="eyebrow">Lending outcome</span>
  <h2>More approvals at every level of risk</h2>
  <p>Each point is a cut-off. At any approval rate the engine's book carries less risk, because it sizes every offer to
  the borrower's real income and catches applicants whose stated income is inflated.</p>
  <div class="fig">{curve}</div>
  <div class="tablewrap"><table>
    <thead><tr><th>Policy</th><th class="num">Approved</th><th class="num">Thin-file approved</th><th class="num">Bad rate</th>
    <th class="num">Loss rate</th><th class="num">Volume ₾</th><th class="num">Hidden PTI breaches</th><th class="num">Income-fakers approved</th></tr></thead>
    <tbody>{prow(tr, "Traditional")}<tr class="hl">{prow(en, "Engine, recommended approvals")[4:]}{prow(em, f"Engine at traditional's bad rate (PD ≤ {em['pd_threshold']:.0%})")}</tbody>
  </table></div>
  <p class="note">Hidden PTI breach: an approval whose payments exceed the NBG limit on the borrower's true income. Loss rate uses an assumed 55% loss given default for unsecured retail. Review queue: {P['review_queue_share']:.0%} of applications go to an officer with flags.</p>
</section>

<section>
  <span class="eyebrow">Step 1 · Income</span>
  <h2>Real income, not stated income</h2>
  <p>Declared income is off by a median {I['mdape_declared']:.0%}; adding up every inflow is worse ({I['mdape_naive_inflows']:.0%}) because
  it counts own-account transfers, gifts and circular money. The engine removes those, infers cash and other-bank income
  from spending, and gives a P10–P90 band that contains the true income {I['band_coverage_p10_p90']:.0%} of the time (target 80%).</p>
  <div class="fig">{inc_chart}</div>
  <p class="note">Income-fakers ({rt['n']} in the test set): declared income overstated by {rt['declared_overstatement']:.0%}, sum of inflows by
  {rt['naive_overstatement']:.0%}, engine estimate by {rt['engine_overstatement']:+.0%}. Transactions categorised with {M['categoriser']['accuracy']:.1%} accuracy
  (macro F1 {M['categoriser']['macro_f1']:.2f}) from mixed Georgian and Latin descriptions.</p>
</section>

<section>
  <span class="eyebrow">Step 2 · Risk</span>
  <h2>A transparent scorecard won the champion slot</h2>
  <p>We trained a gradient-boosting model and a logistic scorecard on the same features. The simpler model is kept unless the
  complex one is clearly better; on validation it was not ({R['champion_selection']['auc_scorecard']:.3f} vs {R['champion_selection']['auc_gbm']:.3f} AUC), so the
  scorecard decides and every reason is exact. It reaches {R['share_of_oracle_gini']:.0%} of the best Gini any model could achieve on this data.</p>
  <div class="two"><div class="fig">{roc}</div><div class="fig">{calib}</div></div>
  <div class="tablewrap"><table><thead><tr><th>Out-of-time AUC</th><th class="num">All applicants</th><th class="num">Thin file</th><th class="num">With bureau</th></tr></thead><tbody>
    <tr class="hl"><th scope="row">Engine (champion)</th><td class="num">{R['engine']['auc']:.3f}</td><td class="num">{R['thin_file']['engine']['auc']:.3f}</td><td class="num">{R['with_bureau']['engine']['auc']:.3f}</td></tr>
    <tr><th scope="row">Traditional bureau model</th><td class="num">{R['traditional_bureau']['auc']:.3f}</td><td class="num">{R['thin_file']['traditional_bureau']['auc']:.3f}</td><td class="num">{R['with_bureau']['traditional_bureau']['auc']:.3f}</td></tr>
    <tr><th scope="row">Ceiling: true default probability</th><td class="num">{R['oracle_true_pd']['auc']:.3f}</td><td class="num">{R['thin_file']['oracle_true_pd']['auc']:.3f}</td><td class="num">–</td></tr>
  </tbody></table></div>
</section>

<section>
  <span class="eyebrow">Step 3 · Path to yes</span>
  <h2>Loans shaped like a harvest</h2>
  <p>For {M['seasonal']['n']:,} seasonal borrowers, a repayment schedule that follows their income, with the same present value for the lender,
  cuts the true default probability from {M['seasonal']['true_pd_annuity']:.1%} to {M['seasonal']['true_pd_seasonal']:.1%}
  ({M['seasonal']['relative_reduction']:.0%} lower). Declined applicants also see the largest compliant amount for each term.</p>
  <div class="fig">{seas}</div>
  <p class="note">Example: a Kakheti grape grower's first 12 instalments in GEL. How NBG's PTI rule applies to non-equal schedules must be confirmed with NBG.</p>
</section>

<section>
  <span class="eyebrow">Fairness</span>
  <h2>Narrower gaps between regions and ages</h2>
  <p>Gender, age and region are never model inputs; we use them only to audit outcomes. At the same bad rate as the traditional process,
  the approval-rate gap between regions falls from {F['region']['traditional_parity_gap']:.0%} to {F['region']['engine_parity_gap']:.0%} and between age groups from
  {F['age_band']['traditional_parity_gap']:.0%} to {F['age_band']['engine_parity_gap']:.0%}. Gender gap: {F['gender']['engine_parity_gap']:.1%}.</p>
  <div class="two"><div class="fig"><h3>By region</h3>{fair_r}</div><div class="fig"><h3>By age group</h3>{fair_a}</div></div>
</section>

<section>
  <span class="eyebrow">Model risk &amp; guardrails</span>
  <h2>Controls a supervisor can check</h2>
  <div class="two">
    <div class="tablewrap"><table><thead><tr><th>Business-logic sign check</th><th>Expected</th><th class="num">Coef.</th><th>Status</th></tr></thead><tbody>{signs}</tbody></table></div>
    <div style="display:grid;gap:14px;align-content:start">
      <div class="tablewrap"><table><thead><tr><th>Drift, PSI 2025→2026</th><th class="num">PSI</th><th>Status</th></tr></thead><tbody>{psi_rows}</tbody></table></div>
      <ul class="plain">
        <li>Counter-intuitive features are dropped automatically and logged.</li>
        <li>Offers can never exceed the NBG PTI/LTV limit; rules are versioned by date, with the 2027 thresholds pre-loaded.</li>
        <li>Lari −20% stress: average PD on USD loans to GEL earners rises from {M['stress_gel_minus20']['pd_base']:.1%} to {M['stress_gel_minus20']['pd_stressed']:.1%}.</li>
        <li>Every officer decision and override is written to a hash-chained audit log; overrides need a written reason.</li>
        <li>{M['latency']['single_application_ms']:.0f} ms per application; {M['latency']['batch_applications_per_sec']:,.0f} applications per second in batch on one CPU.</li>
      </ul>
    </div>
  </div>
</section>

<section>
  <span class="eyebrow">For NBG supervisors</span>
  <h2>What the 2027 PTI thresholds do to this pool</h2>
  <p>NBG will apply the 25% PTI limit to incomes below 2,000 ₾ from 1 February 2027 and below 2,500 ₾ from 1 September 2027.
  Re-running the same rules engine: {sup['affected_share']:.0%} of applicants get a lower maximum loan, and total compliant credit
  changes by {sup['credit_change']:+.1%} ({sv['2026-10-20']['credit'] / 1e6:,.1f} M → {sv['2027-02-01']['credit'] / 1e6:,.1f} M → {sv['2027-09-01']['credit'] / 1e6:,.1f} M ₾).</p>
  <div class="fig">{sup_chart}</div>
</section>

<section>
  <span class="eyebrow">Limitations</span>
  <h2>What we have not proven yet</h2>
  <ul class="plain">
    <li>All results come from synthetic data calibrated to Georgian patterns. Real performance is unknown until a pilot in NBG's AI sandbox.</li>
    <li>In production the income model needs verified income labels (payroll, Revenue Service data or documents) for training.</li>
    <li>Lenders observe outcomes only for approved loans; a real model needs reject inference.</li>
    <li>Circular transfers returned through a different account are missed (detection recall {M['round_trip_detection']['recall']:.0%}, precision {M['round_trip_detection']['precision']:.0%}); flagged cases go to an officer.</li>
    <li>{en['hidden_pti_breaches']} of {en['approved']:,} engine approvals ({en['hidden_pti_breaches'] / en['approved']:.0%}) would breach PTI on the borrower's true income, against {tr['hidden_pti_breaches'] / tr['approved']:.0%} for the traditional process. Basing PTI on P10 instead of P25 income lowers this at the cost of approvals.</li>
  </ul>
</section>

<footer>Income Truth Engine {M['model_version']} · generated {M['generated_at']} · synthetic data only, no real customers ·
Sources for rules: NBG "PTI and LTV Requirements"; NBG Financial Stability Committee decision on 2027 PTI thresholds.</footer>
</div>"""
    return html


def main():
    M = json.loads((REP / "metrics.json").read_text())
    cfg = rules.load()
    sup = supervisor(cfg)
    M["supervisor_2027"] = sup
    (REP / "metrics.json").write_text(json.dumps(M, indent=2, ensure_ascii=False, default=float))
    pngs(M, sup)
    cards(M)
    (REP / "results.html").write_text(page(M, sup))
    print("ok", sup)


if __name__ == "__main__":
    main()
