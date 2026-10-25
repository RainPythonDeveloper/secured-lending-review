# Data card

**Status:** 100% synthetic. No real person, account or bank is represented.
Generator `src/ite/synth.py` v2.0, seed 42; rerun to reproduce exactly.

| | |
|---|---|
| Borrowers | 8,000 (cohort A: applications Jul 2025, cohort B: Jul 2026) |
| Transactions | 1,373,381 over 18 months before each application |
| Default rate (12 months) | 9.3% (A 8.6%, B 10.1%) |
| Thin-file share | 37.6% |
| Income-faking (round-trip) share | 2.5% |

**Borrower types:** salaried (Tbilisi), farmers (Kakheti, Aug–Oct harvest), self-employed (Imereti),
remittance households (Samegrelo, USD inflows), young first-time borrowers.

**Realism built in:** cash income and income at other banks that the model cannot see; own-account
transfers; one-off inflows; generic or mixed Georgian/Latin transaction descriptions; circular
transfers used to fake income (some returned through a different account, some legitimate refunds
that look the same); a latent "fragility" trait and post-application shocks that no feature captures;
drift between cohorts (higher rates, slightly higher default rate in 2026).

**Default mechanism (hidden ground truth):** `sigmoid(-3.5 + 2.5*(burden-0.35) + 2.5*max(0,burden-0.6) + 1.2*max(0,stress-0.6) + 0.9*fx_mismatch + 2*gambling + 4*gambling*(savings<3%) + 4*max(0,late_rate-0.15) - 6*min(savings,10%) + fragility + 1.6*shock + drift)`

**Columns never given to any model:** every `TRUE_*` column, `category_true` (used only to train the
transaction categoriser, standing in for a bank's labelled history) and `is_round_trip`.

**Calibrate before real use:** Geostat average wages by region, Geostat Integrated Household Survey, NBG USD/GEL monthly rates, NBG retail loan interest rates.
