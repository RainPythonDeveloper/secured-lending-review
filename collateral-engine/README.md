# Collateral second opinion

**NBG AI & Open Banking Hackathon 2026 · Track 1: AI in Finance · AI1: Credit Risk & Lending**

A loan officer in Tbilisi receives a licensed valuer's report on the flat or private house offered as
collateral, or an application for a car loan. This service gives an independent second opinion. It
values the property or vehicle from comparable sales with a
calibrated range, reads the declared condition from interior photos, flags an appraisal outside the
market range, and computes the NBG loan-to-value check. The officer decides, and every assessment and
decision goes to a tamper-evident audit log.

> All data is synthetic. No real person, property, valuer or transaction is represented.

## Results on synthetic data

Out-of-time backtest on sales from 21 July to 20 October 2026, each valued only from sales before
its own date and only with comparables within the NBG 84/04 adjustment limits, with the range
calibrated on the six months before. Flats are valued from flats and houses from houses, each with
its own hedonic rates and range. `make evaluate` reproduces it.

| Metric | Flats | Houses | Reference |
|---|---|---|---|
| Sales tested | 528 | 96 | |
| Median absolute error | 8.4% | 11.0% | |
| Range coverage | 77.1% | 71.9% | target 80% |
| Coefficient of dispersion (COD) | 9.7 | 14.2 | IAAO ≤ 15 for residential |
| Price-related differential (PRD) | 1.013 | 1.025 | IAAO 0.98–1.03 |
| Slope of ln(ratio) on ln(estimate) | 0.013 | 0.041 | gate ±0.05 |
| Sales without enough comparables | 0 | 2 | |

The sales are synthetic, so these numbers check the method and its implementation, not real-world
accuracy. Coverage is below target because prices drift between the calibration and test windows;
`tests/test_evaluation.py` fails the build if any metric leaves its gate. For houses the PRD is
reported but not gated: the 14% noise in synthetic house prices alone puts it near 1.03 even for
unbiased estimates, so regressivity is gated on the slope against the estimate instead.

Vehicles, same out-of-time design on synthetic sales of 14 models:

| Metric | Vehicles | Gate |
|---|---|---|
| Sales tested | 398 of 400 | ≥ 90% valued |
| Median absolute error | 7.7% | ≤ 10% |
| Within ±10% / ±20% | 62% / 94% | |
| Range coverage | 80.2% | target 80% ± 8 points |

## Georgian and NBG specifics

| Topic | How the service handles it |
|---|---|
| NBG LTV limits | Read from `income-engine/config/nbg_rules.yaml`, the same dated file that holds the PTI limits. Since the NBG easing published on 26 Feb 2025: 90% for GEL loans secured by real estate (85% before), 70% for foreign-currency loans, 80% for foreign-currency mortgages of borrowers with income from abroad. The version in force on the application date applies. |
| NBG valuation rules (Order 84/04) | At least 3 comparables; each adjustment within ±15% and the gross adjustment within ±25% (Art. 4(5)). Sales beyond the limits are not used; if too few remain, sales up to ±35% gross are used and the report asks for a written justification; if still too few, a valuer has to inspect. The limits are in the same dated rules file. |
| Exchange rate | Official NBG rate from the nbg.gov.ge public API. The API answers an unpublished date with the latest rate, so the date of every answer is checked. |
| Currency | Tbilisi flats trade in USD, and loans are mostly in GEL. The value is converted at the NBG rate, and the report shows the LTV if the lari strengthens by 20%. Money is `Decimal` and travels as a decimal string. |
| Property identity | NAPR cadastral code, Tbilisi (region `01`) only. A flat's code has building and unit segments (`01.14.14.011.008.01.527`); a house's code is the parcel code (`01.15.09.214.033`). |
| Market prices | Synthetic sales anchored to Geostat's Q1 2026 price per m² of new flats and of new private houses in each of the ten Tbilisi districts (offer prices from myhome.ge and ss.ge). House prices grow 5.5% a year, the Geostat Q2 2026 figure. |
| Private houses | House area, land plot area and number of storeys. Comparables are houses only, searched within 3 km (5 km if too few) and 24 months, and ranked by plot size as well; land is a separate adjustment in the grid. Houses under construction are rejected. |
| Vehicles | NBG Order 84/04 covers real estate only and NBG sets no LTV limit for vehicle loans, so the limit (70%), the maximum age at the end of the loan (12 years) and the photo set (front, rear, both sides, odometer, VIN plate) are bank policy in `config/vehicle_policy.yaml`. Comparables are earlier sales of the same make and model; the report projects the value to the end of the loan. Georgian risks are flagged: no customs clearance (the vehicle cannot be registered or pledged), accident history (many imports come from US auctions), right-hand drive, and a gas conversion is priced. VIN (ISO 3779) and the Georgian plate format are validated. There is no official used-car price series, so the synthetic market rests on stated demo assumptions. |
| Land without a building | Not valued by the model: Georgia has no official land price series and NAPR publishes no transaction prices. A valuer's report on land goes through the 84/04 report check. |
| Flats under construction | Developer, construction stage, completion date and NAPR registration of the purchase agreement; comparables are other unfinished buildings (the 84/04 limits rule out larger status adjustments); the lending value is cut by a bank-policy factor per stage (70% foundation to 95% finishing); overdue or distant completion and an unregistered agreement are flagged. |
| Condition | The seven classes of Georgian listings: black, white and green frame (შავი, თეთრი, მწვანე კარკასი), needs renovation, under renovation, old renovation, newly renovated. |
| Location | The ten Tbilisi districts and the distance to the nearest of 23 metro stations (OpenStreetMap). |
| Language | Every reason, status and label is in Georgian and English. |

## Run it

```bash
make install        # Python 3.12 virtual environment with pinned dependencies
make data           # 6,000 flat and 1,200 house sales -> data/comparables.csv,
                    # 8,000 vehicle sales -> data/vehicle_sales.csv (all synthetic)
make app            # officer console on http://localhost:8502 (restart it after editing src/)
make api            # REST API on http://localhost:8100/docs
make check          # ruff format --check, ruff check, pytest (389 tests, about 25 s)
make evaluate       # backtest of flats, houses and vehicles -> reports/metrics.json
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
| `cadastral_code` | text | NAPR code in Tbilisi: with unit segments for a flat, parcel code for a house |
| `property_kind` | text | `flat` or `house` |
| `land_area_m2` | decimal | plot area of a house, 20–100000; empty for a flat |
| `district` | text | one of the ten district codes, for example `vake` |
| `latitude`, `longitude` | decimal | WGS 84, inside Tbilisi |
| `sale_date` | date | ISO 8601 |
| `price_usd` | decimal | registered price, USD |
| `total_area_m2` | decimal | 15–1000 |
| `rooms`, `floor`, `building_floors` | integer | floor not above the top floor; a house has floor 1 and its storeys in `building_floors` |
| `building_status` | text | `new_building`, `old_building`, `under_construction` |
| `condition` | text | one of the seven condition classes |

Vehicle sales follow `VehicleSale` in `src/collateral_engine/vehicles/market.py` and are read from
`COLLATERAL_VEHICLE_MARKET_DATA_PATH`:

| Column | Type | Rule |
|---|---|---|
| `sale_id` | text | letters, digits, `-` |
| `make`, `model` | text | matched without regard to case |
| `production_year` | integer | 1990–2030 |
| `mileage_km` | integer | 0–1,000,000 |
| `engine_volume_cm3` | integer | 0 exactly for an electric vehicle |
| `fuel` | text | `petrol`, `diesel`, `hybrid`, `petrol_gas`, `electric` |
| `steering` | text | `left`, `right` |
| `is_customs_cleared`, `has_accident_history` | boolean | |
| `sale_date` | date | ISO 8601 |
| `price_usd` | decimal | sale price, USD |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Model version and number of comparable sales |
| GET | `/v1/reference/districts` | Districts with Georgian and English names and Geostat prices |
| GET | `/v1/exchange-rates/usd?rate_date=` | NBG official USD rate |
| POST | `/v1/valuations` | Multipart: `request` (ValuationRequest JSON) and `photos`; returns the report |
| POST | `/v1/valuer-reports/check` | Checks a licensed valuer's report (any real estate, including factories) against NBG Order 84/04; each finding names its article |
| POST | `/v1/vehicle-valuations` | Multipart: `request` (VehicleValuationRequest JSON) and `photos`; returns the vehicle report with the bank LTV and the value at the end of the loan |
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
| `COLLATERAL_VEHICLE_MARKET_DATA_PATH` | `data/vehicle_sales.csv` |
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
against the same schema as Claude's. The free hosted endpoint often answers 503 "ResourceExhausted" when
its shared workers are busy; such answers (and 429, 5xx) are retried up to three times with
exponential backoff and jitter, while a timeout or a rejected key leaves the photo unassessed. The Claude request uses server-side refusal fallback (`fallbacks: "default"`), so a declined
request is retried on another model inside the same call; a final refusal leaves the photo
unassessed.

## Limitations

- The comparable sales are synthetic. Real accuracy is known only after a pilot on registered
  transactions (NAPR) or a bank's appraisal database.
- Listing prices differ from transaction prices; calibrate before using listings as comparables.
- The condition reading has not been measured on labelled photos; the vision path is tested with
  a stand-in client only.
- The cadastral code format is inferred from registry extracts; verify it against the NAPR rule.
- Flats and private houses in Tbilisi only. Land and commercial property get the valuer report
  check, not a model valuation.
- Vehicle photos are checked for quality and reuse only; the odometer and VIN plate are not read
  from them yet, and the declared mileage and accident history are not verified.
- Geostat's house prices are offer prices of new houses. Per the IMF technical assistance report
  on the Georgian RPPI (April 2025), Geostat's house model takes floor area and plot area as
  separate characteristics, so the price per m² is per m² of the house, as in this model. Listings
  may give the plot area without the building footprint, while NAPR includes it; align the two
  before using real sales.
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
