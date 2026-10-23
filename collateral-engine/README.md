# Collateral second opinion

**NBG AI & Open Banking Hackathon 2026 · Track 1: AI in Finance · AI1: Credit Risk & Lending**

A loan officer in Tbilisi receives a licensed valuer's report on the flat offered as collateral.
This service gives an independent second opinion. It values the flat from comparable sales with a
calibrated range, reads the declared condition from interior photos, flags an appraisal outside the
market range, and computes the NBG loan-to-value check. The officer decides, and every assessment and
decision goes to a tamper-evident audit log.

> All data is synthetic. No real person, flat, valuer or transaction is represented.

## Results on synthetic data

Out-of-time backtest: 528 sales from 21 July to 20 October 2026, each valued only from sales before
its own date and only with comparables within the NBG 84/04 adjustment limits, with the range
calibrated on the six months before. `make evaluate` reproduces it.

| Metric | Value | Reference |
|---|---|---|
| Median absolute error | 8.4% | |
| Within ±10% / ±20% | 59% / 91% | |
| Range coverage | 77.1% | target 80% |
| Coefficient of dispersion (COD) | 9.7 | IAAO ≤ 15 for residential |
| Price-related differential (PRD) | 1.013 | IAAO 0.98–1.03 |
| Sales without enough comparables | 0 of 528 | |

The sales are synthetic, so these numbers check the method and its implementation, not real-world
accuracy. Coverage is slightly below target because prices drift between the calibration and test
windows; `tests/test_evaluation.py` fails the build if any metric leaves its gate.

## Georgian and NBG specifics

| Topic | How the service handles it |
|---|---|
| NBG LTV limits | Read from `income-engine/config/nbg_rules.yaml`, the same dated file that holds the PTI limits. Since the NBG easing published on 26 Feb 2025: 90% for GEL loans secured by real estate (85% before), 70% for foreign-currency loans, 80% for foreign-currency mortgages of borrowers with income from abroad. The version in force on the application date applies. |
| NBG valuation rules (Order 84/04) | At least 3 comparables; each adjustment within ±15% and the gross adjustment within ±25% (Art. 4(5)). Sales beyond the limits are not used; if too few remain, sales up to ±35% gross are used and the report asks for a written justification; if still too few, a valuer has to inspect. The limits are in the same dated rules file. |
| Exchange rate | Official NBG rate from the nbg.gov.ge public API. The API answers an unpublished date with the latest rate, so the date of every answer is checked. |
| Currency | Tbilisi flats trade in USD, and loans are mostly in GEL. The value is converted at the NBG rate, and the report shows the LTV if the lari strengthens by 20%. Money is `Decimal` and travels as a decimal string. |
| Property identity | NAPR cadastral code (`01.14.14.011.008.01.527`). Only Tbilisi (region `01`) flats with building and unit segments are accepted. |
| Market prices | Synthetic sales anchored to Geostat's Q1 2026 average price per m² in each of the ten Tbilisi districts. |
| Condition | The seven classes of Georgian listings: black, white and green frame (შავი, თეთრი, მწვანე კარკასი), needs renovation, under renovation, old renovation, newly renovated. |
| Location | The ten Tbilisi districts and the distance to the nearest of 23 metro stations (OpenStreetMap). |
| Language | Every reason, status and label is in Georgian and English. |

## Run it

```bash
make install        # Python 3.12 virtual environment with pinned dependencies
make data           # 6,000 synthetic comparable sales -> data/comparables.csv
make app            # officer console on http://localhost:8502 (restart it after editing src/)
make api            # REST API on http://localhost:8100/docs
make check          # ruff format --check, ruff check, pytest (280 tests, about 20 s)
make evaluate       # backtest -> reports/metrics.json
```

From the repository root: `docker compose up --build collateral-engine-api collateral-console`.
The image is built from the repository root so it carries the shared NBG rules file.

To read condition from photos, set `COLLATERAL_VISION_ENABLED=true` and `NVIDIA_API_KEY` (hosted
NVIDIA model `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, the default). For Claude instead, set
`COLLATERAL_VISION_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`. Without a provider, photos are still
checked and hashed, and the condition stays INCONCLUSIVE.
`python -m collateral_engine.vision_check photo.jpg` runs the configured vision model on your own
photos; it calls the hosted API and is not part of the test suite.

## How it works

```
application (cadastral code, district, location, area, floors, declared condition, loan, appraisal)
   │                                              photos
   │                                                │
   │                    photo checks: SHA-256 evidence store, size, brightness, sharpness,
   │                    perceptual hash (same photo twice, or seen in another application)
   │                                                │ usable photos, metadata stripped
   │                    vision model → one JSON object per photo (strict schema, else discarded)
   │                                                │
   │                    condition rules (YAML) → VERIFIED / PARTLY / CONTRADICTED / INCONCLUSIVE
   ▼                                                │ condition the evidence supports
comparable sales before the valuation date ─▶ adjustment grid (time, location, condition,
   within 1.5 km (3 km once), 18 months,        building, floor, size) with hedonic rates
   similar size, adjustments within 84/04     ─▶ weighted median ─▶ conformal 80% range
                                              ─▶ hedonic challenger (disagreement > 15% → review)
   │
   ├─ licensed appraisal vs range → second opinion
   ├─ lending value = lower of appraisal and model estimate (range low without appraisal)
   ├─ NBG LTV check at the NBG rate, plus lari +20% stress
   ▼
reason codes → recommendation (accept / officer review / physical inspection; never reject)
   ▼
officer decision (reason required against the recommendation) → hash-chained audit log
```

| Path | What |
|---|---|
| `src/collateral_engine/domain.py`, `cadastral.py` | Request vocabulary and NAPR cadastral codes |
| `market.py`, `synth.py` | Comparable-sales data contract, loader and synthetic generator |
| `hedonic.py`, `comparables.py`, `valuation.py` | Hedonic rates, comparable selection, adjustment grid, calibrated range |
| `photos.py`, `vision.py`, `nvidia_vision.py`, `condition.py` | Photo checks, Claude and NVIDIA vision clients, condition rules |
| `nbg_rules.py`, `ltv.py`, `appraisal.py`, `money.py`, `nbg_rates.py` | Dated NBG rules, LTV check, appraisal check, GEL/USD, NBG rate client |
| `findings.py`, `flags.py` | Reason codes and recommendation |
| `engine.py` | The single assessment path for API and console |
| `audit.py`, `photo_registry.py`, `evidence.py` | Audit log, photo reuse registry, evidence store |
| `evaluation.py` | Backtest with IAAO ratio statistics |
| `api.py` | FastAPI service |
| `i18n.py`, `ui_text.py` | Georgian and English texts |
| `app/` | Officer console (Streamlit) |
| `config/` | Valuation policy and condition rules (versioned YAML) |

## Data contract for comparable sales

A bank or NBG plugs in its own sales by exporting this CSV and pointing
`COLLATERAL_MARKET_DATA_PATH` at it. The loader rejects the file and names the line and field of
every invalid row.

| Column | Type | Rule |
|---|---|---|
| `sale_id` | text | letters, digits, `-` |
| `cadastral_code` | text | NAPR code of a flat in Tbilisi |
| `district` | text | one of the ten district codes, for example `vake` |
| `latitude`, `longitude` | decimal | WGS 84, inside Tbilisi |
| `sale_date` | date | ISO 8601 |
| `price_usd` | decimal | registered price, USD |
| `total_area_m2` | decimal | 15–1000 |
| `rooms`, `floor`, `building_floors` | integer | floor not above the top floor |
| `building_status` | text | `new_building`, `old_building`, `under_construction` |
| `condition` | text | one of the seven condition classes |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Model version and number of comparable sales |
| GET | `/v1/reference/districts` | Districts with Georgian and English names and Geostat prices |
| GET | `/v1/exchange-rates/usd?rate_date=` | NBG official USD rate |
| POST | `/v1/valuations` | Multipart: `request` (ValuationRequest JSON) and `photos`; returns the report |
| POST | `/v1/valuer-reports/check` | Checks a licensed valuer's report (any real estate, including factories) against NBG Order 84/04; each finding names its article |
| POST | `/v1/valuations/{valuation_id}/decision` | Officer decision; 422 `REASON_REQUIRED` against the recommendation without a reason |
| GET | `/v1/audit/verify` | Checks the hash chain |

Errors are `application/problem+json` with `type`, `title`, `status`, `code` and `detail`, as in
the Open Banking gateway of this repository.

## Guardrails in code

| Guardrail | Where |
|---|---|
| The vision model only describes photos; versioned YAML rules set the status | `vision.py`, `condition.py`, `config/condition_rules.yaml` |
| Vision answers off the JSON schema are discarded; refusals, truncation and outages leave the photo unassessed | `vision.py` (`parse_assessment_response`) |
| A bad photo or failed model gives INCONCLUSIVE, never CONTRADICTED | `photos.py`, `condition.py` |
| At least 3 photos of the flat; fewer is flagged and goes to officer review | `config/condition_rules.yaml` (`min_photos`), `findings.py` |
| Photos showing people are excluded; photo metadata (GPS) is stripped before leaving the bank | `condition.py`, `photos.py` (`prepare_for_vision`) |
| No automatic rejection; the strongest outcome is a physical inspection | `flags.py` |
| Deciding against the recommendation needs a written reason | `audit.py` (`record_officer_decision`) |
| Evidence photos are stored by SHA-256 and listed in the hash-chained audit log | `evidence.py`, `audit.py` |
| A valuation never uses sales on or after its date | `comparables.py`, `tests/test_valuation.py` |
| Comparables respect NBG Order 84/04 Art. 4(5): ≥3 sales, each adjustment ≤ ±15%, gross ≤ ±25% (±35% only with a justification flag) | `comparables.py`, `valuation.py` (`adjustment_screen`), `nbg_rules.py` |
| NBG rule values live only in the dated rules file | `nbg_rules.py`, `income-engine/config/nbg_rules.yaml` |
| Two independent estimates; large disagreement goes to review | `valuation.py`, `findings.py` |
| No fields about honesty, emotion or biometrics in the report | `tests/test_engine.py` |
| Release gates on accuracy, coverage, COD and PRD | `tests/test_evaluation.py` |
| Money in `Decimal`; limits rounded down | `money.py`, `ltv.py` |

## Configuration

Every variable is optional and listed in `.env.example`. Copy it to `.env` (git-ignored) and
fill in what you need: `make` exports `.env` to `make app`, `make api` and the other targets. An
empty value such as `NVIDIA_API_KEY=` means "not set".

| Variable | Default |
|---|---|
| `COLLATERAL_CONFIG_DIR` | `config/` |
| `COLLATERAL_MARKET_DATA_PATH` | `data/comparables.csv` |
| `COLLATERAL_MARKET_DATA_SOURCE` | text naming the synthetic generator |
| `NBG_RULES_PATH` | `../income-engine/config/nbg_rules.yaml` |
| `COLLATERAL_AUDIT_DB_PATH` | `audit.db` |
| `COLLATERAL_EVIDENCE_DIR` | `evidence/` |
| `COLLATERAL_VISION_ENABLED` | `false` |
| `COLLATERAL_VISION_PROVIDER` | `nvidia` (or `anthropic`) |
| `COLLATERAL_VISION_MODEL` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, or `claude-opus-5-5` for anthropic |
| `NVIDIA_API_KEY` | none; required for the nvidia provider |
| `NVIDIA_CHAT_URL` | `https://integrate.api.nvidia.com/v1/chat/completions` |
| `COLLATERAL_VISION_TIMEOUT_S` | `60` |
| `NBG_RATES_URL` | `https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/` |
| `NBG_RATES_TIMEOUT_S` | `10` |

The NVIDIA endpoint has no strict JSON-schema mode: the schema is in the prompt, thinking is turned
off (`chat_template_kwargs.enable_thinking: false`), temperature is 0, and the answer is validated
against the same schema as Claude's. The Claude request uses server-side refusal fallback (`fallbacks: "default"`), so a declined
request is retried on another model inside the same call; a final refusal leaves the photo
unassessed.

## Limitations

- The comparable sales are synthetic. Real accuracy is known only after a pilot on registered
  transactions (NAPR) or a bank's appraisal database.
- Listing prices differ from transaction prices; calibrate before using listings as comparables.
- The condition reading has not been measured on labelled photos; the vision path is tested with
  a stand-in client only.
- The cadastral code format is inferred from registry extracts; verify it against the NAPR rule.
- Flats in Tbilisi only. Houses, land and commercial property are out of scope.
- The API does not authenticate callers; run it on localhost or a private network.
- Have a native speaker review the Georgian texts.

## Third-party components

Licences as declared by the installed packages.

| Component | Version | Licence | Used for |
|---|---|---|---|
| anthropic | 1.12.1 | MIT | Vision model client |
| fastapi | 0.159.1 | MIT | REST API |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| python-multipart | 0.0.32 | Apache-2.0 | Photo upload |
| pydantic | 2.14.1 | MIT | Validation at every boundary |
| numpy | 2.5.4 | BSD-3-Clause and others | Numerics |
| pandas | 3.0.6 | BSD-3-Clause | Sales tables |
| pillow | 13.0.0 | MIT-CMU | Photo checks |
| httpx | 0.28.1 | BSD-3-Clause | NBG rate client |
| PyYAML | 6.0.3 | MIT | Configuration |
| streamlit | 1.66.1 | Apache-2.0 | Officer console |
| pydeck | 0.9.3 | Apache-2.0 | Map |
| pytest, ruff (dev) | 9.1.1, 0.16.10 | MIT | Tests and lint |
| OpenStreetMap metro stations | 2026-10-22 | ODbL 1.0, © OpenStreetMap contributors | `reference/tbilisi_metro_stations.json` |
| Geostat district prices | Q1 2026 | public statistics | Synthetic price anchors |
| NBG official exchange rate API | – | public service of the National Bank of Georgia | USD/GEL rate |
| NVIDIA hosted API (Nemotron 3 Nano Omni) | – | NVIDIA API Trial Terms; model under NVIDIA Open Model Agreement | Condition from photos, default provider |
| Claude API | – | commercial service of Anthropic | Condition from photos, alternative provider |
