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
| NBG PTI limits | Same dated rules file: for income below 1,500 GEL 25% (hedged) and 20% (unhedged), above it 50% and 30%. Existing obligations from the credit report count towards the payment. |
| Maturity and FX lending | Longest term: 4 years for unsecured consumer loans (the pipeline applies it to car loans too), 20 years for mortgages, 10 years for FX mortgages. A loan below 750,000 GEL (from 1 Aug 2025) or 1,000,000 GEL (from 1 Jul 2026) must be in GEL when the income is in GEL. These values come from secondary sources and are marked VERIFY in the rules file. |
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
make install        # Python 3.12 environment with this engine and ../income-engine, pinned
make data           # 6,000 flat and 1,200 house sales -> data/comparables.csv,
                    # 8,000 vehicle sales -> data/vehicle_sales.csv, and the income engine's
                    # synthetic borrowers and trained models in ../income-engine (about 2 min)
make app            # platform console on http://localhost:8502 (restart it after editing src/)
make api            # platform API on http://localhost:8100/docs
make check          # ruff, then the tests of both engines (579 tests, about 45 s)
make evaluate       # backtest of flats, houses and vehicles -> reports/metrics.json
```

From the repository root: `docker compose up --build platform-api platform-console`. The image is
built from the repository root so it carries the income engine and the shared NBG rules file.

### Loan application pipeline

The console has two pages: an **Overview** for first-time visitors and the **Loan application**,
which runs the checks a loan officer does by hand before a loan is issued, as one pipeline:
applicant, remote identification, loan, automated checks, officer's decision. One language selector serves both pages.

There are two kinds of applicant:

| Path | Where the data comes from |
|---|---|
| Existing customer | Any of the 100 customers of the organizer dataset (`data/open-banking-synthetic-100-customers.xlsx`). Accounts and six months of transactions come through the Open Banking gateway in `server/` after the customer's consent; the bank's own records (the same workbook) are the fallback when the gateway or the sandbox is down. |
| New customer | A synthetic applicant generated from a profile, a declared income and a seed: a six-month statement in the dataset's format, with income that differs from the declared figure the way real statements do. |

The pipeline (`src/collateral_engine/lending/`) runs five stages:

| Stage | What it checks | Source |
|---|---|---|
| Identity and watchlists | Liveness check of an applicant identified remotely (step 2, below); name against the sanctions/PEP list and the NAPR Debtors Registry | the browser session; synthetic stand-ins in `config/screening_lists.yaml` |
| Credit history | Thin file, current obligations (counted in PTI), days past due in the last 12 months | synthetic stand-in for Creditinfo Georgia, deterministic per customer |
| Income | Whole calendar months of the statement: verified income is the median month, PTI uses the lower-quartile month; declared income above the verified one, unstable income, short history; salary and pension count as documented (stand-in for RS.ge), other income is flagged as undocumented | the statement |
| Affordability | PTI limit by income and currency hedge, GEL lending below the FX threshold, longest term per product; the highest amount within PTI | `income-engine/config/nbg_rules.yaml`, version in force on the application date |
| Collateral | Mortgage: a flat or house through the collateral engine; car loan: a vehicle; consumer loan: none | collateral engine, NBG LTV or bank vehicle policy |

For a mortgage or a car loan, step 2 asks for the collateral in one of two ways:

| Collateral data | What the officer does |
|---|---|
| Demo case | Picks one of five flats and houses or three cars; a summary card shows what the case contains and highlights its risks (right-hand drive, no customs clearance, accident history). |
| Fill in myself | Fills in every field: for real estate the NAPR cadastral code, district, coordinates, area, rooms, floor, building status, declared condition, the off-plan details of a building under construction and the licensed appraisal; for a car the VIN, plate, make, model, year, mileage, engine, fuel, steering, customs clearance and accident history. The form starts from the chosen demo case, so only what differs needs typing. |

Photos are uploaded in both modes. The verdict lists the concrete reasons behind it. The
**Collateral · AI analysis** tab opens first and starts with the AI analysis of the photos, naming
the vision model: for a flat or house the declared condition against what the model sees; for a car
the odometer, VIN, body damage, steering side and the required views, each with its status, and
every photo with what the model read from it. Then come the market value and calibrated range
against the licensed appraisal, the LTV check (NBG for real estate, bank policy for cars) with the
lari stress, the map of the property, comparable sales and metro, the adjustment grid with the NBG
Order 84/04 limits, the model and rule versions, and a check of a valuer's report against Order
84/04. The **Audit log** tab lists the application's records and verifies the hash chain.

| AI check of car photos | Rule (`vision` in `config/vehicle_policy.yaml`) | Outcome when contradicted |
|---|---|---|
| Odometer | within 10% of the declared mileage; miles are converted to km | officer review; the car is valued at the higher mileage |
| VIN plate | the 17 characters read must equal the declared VIN | physical inspection: the photos may show another car |
| Body damage | major damage on the front, rear or sides without a declared accident | officer review |
| Steering side | read only from cabin photos | officer review |
| Views | front, rear, both sides, odometer, VIN plate | listed as missing |

A reading counts only at medium confidence or higher and never from a photo with people in it;
an unreadable photo leaves the claim INCONCLUSIVE, never CONTRADICTED. One application keeps one
number across reruns, so its own photos are not mistaken for photos reused from another application.

The offer is the request cut to the lowest of the PTI and LTV maximums, rounded down to 100 GEL,
and the report names the binding limit. The recommendation is: compliance review on a watchlist
match, physical inspection when the collateral needs one or cannot be valued, officer review when any stage needs
review, otherwise the full or a reduced offer. There is no automatic refusal. The decision form
starts from the decision that matches the recommendation; any other decision, and every decline,
needs a written reason. The assessment (`LOAN_APPLICATION_ASSESSED`, with the SHA-256 of the
report) and the decision (`LOAN_DECISION`) go to the shared hash-chained audit log. The page shows
the processing time next to the manual minutes the checks replace (`config/lending_policy.yaml`,
an assumption).

**Remote identification (step 2).** NBG Order 104/04 lets a bank identify a customer remotely by
video, with at least three randomly chosen tasks and at most three attempts in 24 hours. The
console draws the tasks on the server (turn the head left or right, look up or down, blink) and
the applicant performs them in front of the camera. MediaPipe Face Landmarker runs in the
browser, follows the head and eye movements against the applicant's own pose while looking at the
camera, and draws the face mesh, the oval and the progress of each task. The browser reports
only what happened; `lending/liveness.py` sets the status from `liveness` in
`config/lending_policy.yaml`:

| Session | Status | Outcome |
|---|---|---|
| Every drawn task done in time, one person in the frame | PASSED | the identity stage passes |
| A task missed, or other tasks than the drawn ones | NOT_PASSED | officer review; a new attempt draws new tasks |
| No camera, the model did not load, the applicant not centred, several people in the frame | INCONCLUSIVE | officer review, never a refusal |

The frames are not stored: one small frame per completed task is shown to the officer in the
session's memory only, and the session (tasks, status, the frames' SHA-256, never the images) goes
to the audit log as `LIVENESS_CHECKED`. No face
template is created, no faces are matched and nothing is inferred about the person: of the
model's outputs only the landmarks and the two eye-blink scores are read. Minors are not filmed.
The step is optional: an applicant identified in person in a branch skips it. The model runs in
the browser from the jsDelivr and Google CDNs, so the camera page needs internet access;
`localhost` counts as a secure context for the camera. Matching the face against an ID document
is out of scope. The thresholds have been set by hand, not measured on a labelled set.

Creditinfo, RS.ge, the sanctions list and the Debtors Registry are synthetic stand-ins, labelled
as such on every stage card, because the hackathon provides no access to them.

**Open Banking consent, step by step.** Start the gateway (`cd ../server && npm run start:dev`, or
`docker compose up`). On the Loan application page pick a customer and press *Request consent*:
the gateway creates a consent bound to that dataset customer at the TBC sandbox. Press *Approve at
the bank*, approve the consent on the sandbox page yourself, come back and press *Load the data*.
Before approval the page says the consent is pending; *Use the bank's records* skips the consent.

The earlier full application (income engine plus collateral) stays available through the API at
`/v1/full-applications`.

To read the photos with AI, set `COLLATERAL_VISION_ENABLED=true` and `NVIDIA_API_KEY` (hosted
NVIDIA model `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, the default). For Claude instead, set
`COLLATERAL_VISION_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`. The same model reads flat interiors
and car photos, each with its own instructions and JSON schema (`vision.py`, `vehicles/vision.py`).
Without a provider, photos are still checked and hashed, and every claim stays INCONCLUSIVE.
`make vision-check ARGS="photo.jpg"` (or `ARGS="--vehicle front.jpg odometer.jpg"`) runs the
configured model on your own photos; it calls the hosted API and is not part of the test suite.
`make app APP_PORT=8504` starts the console on another port.

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
| `lending/` | Loan application pipeline: customer data, Open Banking client, screening, credit report, income analysis, affordability, recommendation, officer decision |
| `app/` | Officer console (Streamlit): overview, loan application, collateral form and report |
| `config/` | Valuation policy, condition rules, lending policy and screening lists (versioned YAML) |

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
| POST | `/v1/income/assessments` | IncomeAssessmentRequest JSON (application and at least 20 consented transactions); returns income P10–P90, the PTI check, the highest compliant amount, default probability and bilingual reasons |
| POST | `/v1/full-applications` | Multipart: `request` (FullApplicationRequest JSON: income plus `real_estate` or `vehicle`) and `photos`; returns both reports, the binding limit, the offer and one recommendation |
| POST | `/v1/valuations/{valuation_id}/decision` | Officer decision; 422 `REASON_REQUIRED` against the recommendation without a reason |
| GET | `/v1/audit/verify` | Checks the hash chain |

Errors are `application/problem+json` with `type`, `title`, `status`, `code` and `detail`, as in
the Open Banking gateway of this repository.

## Guardrails in code

| Guardrail | Where |
|---|---|
| The vision model only describes photos; versioned YAML rules set the status | `vision.py`, `condition.py`, `config/condition_rules.yaml`, `vehicles/evidence.py`, `config/vehicle_policy.yaml` |
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
| Liveness tasks are drawn on the server, at least three (NBG 104/04); the browser cannot choose them or set the status | `lending/liveness.py`, `config/lending_policy.yaml` (`liveness`) |
| At most three liveness attempts per customer in 24 hours, counted from the audit log | `lending/liveness.py` (`attempts_in_last_day`) |
| Liveness frames are not stored; the audit log holds only their SHA-256; no face template, matching or attributes | `lending/liveness.py`, `app/components/liveness/index.html` |
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
| `INCOME_MODELS_DIR` | `../income-engine/models` |
| `INCOME_DATA_DIR` | `../income-engine/data` (synthetic borrowers for the console) |
| `ITE_API_KEY` | none; when set, the income and full-application routes need `X-API-Key` |
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
| `NBG_DATASET_PATH` | `../data/open-banking-synthetic-100-customers.xlsx` |
| `OPEN_BANKING_GATEWAY_URL` | `http://localhost:3000` |
| `OPEN_BANKING_TIMEOUT_S` | `60` (the sandbox injects delays of up to 15 s on each call) |

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
- The AI checks of car photos were tried on real listing photos but not measured on a labelled
  set; the odometer and VIN readings depend on how sharp those photos are.
- The synthetic vehicle market covers 14 models; any other model (a Ford Mustang, say) gets no
  valuation and goes to a physical inspection.
- Geostat's house prices are offer prices of new houses. Per the IMF technical assistance report
  on the Georgian RPPI (April 2025), Geostat's house model takes floor area and plot area as
  separate characteristics, so the price per m² is per m² of the house, as in this model. Listings
  may give the plot area without the building footprint, while NAPR includes it; align the two
  before using real sales.
- The loan pipeline runs in the console only; it has no API route yet.
- Credit history, RS.ge, the sanctions list and the Debtors Registry are synthetic stand-ins; a
  pilot needs the bank's contracts with Creditinfo and access to the RS.ge and NAPR services.
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
| openpyxl | 3.1.5 | MIT | Reading the organizer dataset |
| streamlit | 1.66.1 | Apache-2.0 | Officer console |
| pydeck | 0.9.3 | Apache-2.0 | Map |
| MediaPipe Tasks Vision (browser, jsDelivr CDN) | 0.10.14 | Apache-2.0 | Face landmarks for the liveness check |
| MediaPipe Face Landmarker model | float16/1 | Apache-2.0 | Face landmarks for the liveness check |
| pytest, ruff (dev) | 9.1.1, 0.16.10 | MIT | Tests and lint |
| OpenStreetMap metro stations | 2026-10-22 | ODbL 1.0, © OpenStreetMap contributors | `reference/tbilisi_metro_stations.json` |
| Geostat district prices | Q1 2026 | public statistics | Synthetic price anchors |
| NBG official exchange rate API | – | public service of the National Bank of Georgia | USD/GEL rate |
| TBC Open Banking sandbox (mock) | – | hackathon sandbox | Consented accounts and transactions |
| NVIDIA hosted API (Nemotron 3 Nano Omni) | – | NVIDIA API Trial Terms; model under NVIDIA Open Model Agreement | Condition from photos, default provider |
| Claude API | – | commercial service of Anthropic | Condition from photos, alternative provider |
