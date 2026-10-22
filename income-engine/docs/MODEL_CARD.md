# Model card: Income Truth Engine 1.0.0

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
| Risk (champion) | **scorecard** chosen over the alternative on validation AUC ({'auc_gbm': 0.8532, 'auc_scorecard': 0.8657, 'champion': 'scorecard', 'min_gain_required': 0.005} ) |
| Explanations | Exact per-feature contributions (scorecard) or SHAP (GBM), in Georgian and English |

## Out-of-time performance (cohort B, July 2026)
| Model | AUC | Gini | KS | Brier |
|---|---|---|---|---|
| Engine (champion) | 0.852 | 0.704 | 0.569 | 0.0673 |
| Gradient boosting (challenger) | 0.841 | 0.683 | 0.549 | 0.0693 |
| Traditional bureau model | 0.805 | 0.609 | 0.494 | 0.0756 |
| Theoretical ceiling (true PD) | 0.891 | 0.782 | | |

Thin-file applicants: engine AUC 0.850 vs bureau model 0.744.
The engine reaches 90% of the theoretical maximum Gini.

Income: median error 5.0% vs 13.2% for declared income;
P10–P90 band covers the true income 80% of the time (target 80%).

## Model-risk controls
- Champion–challenger: the simpler model is kept unless the complex one gains more than 0.005 AUC.
- Business-logic sign checks (scorecard). Features with counter-intuitive signs are dropped automatically: `inc_cv`, `loan_to_income`, `season_top3`, `band_width`, `declared_gap`, `inc_yoy`.

| Feature | Expected | Coefficient | Status |
|---|---|---|---|
| pti_est | + | +0.437 | in model |
| stress_est | + | +0.490 | in model |
| burden_p25 | + | +0.176 | in model |
| betting_share | + | +0.020 | in model |
| late_util_rate | + | +0.410 | in model |
| savings_rate | - | -0.672 | in model |
| circular_ratio | + | +0.027 | in model |
| fx_mismatch | + | +0.211 | in model |
| bureau_score | - | -0.304 | in model |
| inc_cv | + | +0.000 | dropped |
| band_width | + | +0.000 | dropped |
| loan_to_income | + | +0.000 | dropped |
| spend_ratio | + | +0.011 | in model |
| declared_gap | + | +0.000 | dropped |
| season_top3 | + | +0.000 | dropped |
| annual_rate | + | +0.102 | in model |
| thin_file | + | +0.075 | in model |
| n_income_months | - | +0.000 | in model |
| inc_yoy | - | +0.000 | dropped |

- Monotone constraints on the GBM challenger for debt burden, betting, late bills, savings, bureau score.
- Gender, age and region are **not** model inputs; they are used only for fairness monitoring.
- Drift monitoring (PSI, A→B): highest annual_rate 0.22, declared_gap 0.01, inc_cv 0.01. PSI above 0.1 triggers review
  (here `annual_rate` drifts because rates rose; the engine flags it as designed).
- Stress test: lari −20% re-scores every USD loan to a GEL earner.
- Tamper-evident audit log (hash chain) of every officer decision and override.

## Known limitations
- Trained and tested on synthetic data; performance on real data is unknown until a sandbox pilot.
- Income model training needs verified income labels (payroll, Revenue Service data or documents).
- Banks only observe outcomes for approved loans (selection bias); real deployment needs reject inference.
- Circular-transfer detection misses transfers returned through a different account.
- How NBG's PTI rule applies to non-equal (harvest-shaped) schedules must be confirmed with NBG.
