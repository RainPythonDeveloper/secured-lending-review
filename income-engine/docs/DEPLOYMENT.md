# Deployment

## Today (hackathon demo)

| Option | Steps |
|---|---|
| **Testable URL (free)** | Push this repo to GitHub → share.streamlit.io → New app → `app/streamlit_app.py`. Data and models are in the repo, so it starts immediately. Add the URL and "no login needed" to the submission email. |
| **Docker** | On its own: `docker build -t income-engine .` in `income-engine/` → API on :8000 (`/docs` for Swagger). As part of the platform: `docker compose up --build` from the repository root → platform API on :8100, console on :8502. Both images regenerate data, retrain and run the tests at build time, so a broken model cannot ship. |
| **Local** | `pip install -r requirements.txt && make all && make app` |

## Path to production at national scale

Georgia has roughly 3.7 million people; even if every retail loan application in the country went
through the engine, the load is small for this design. Measured on one CPU core: ~150 ms per
application through the API code path and ~2,000 applications per second in batch.

| Layer | Production choice |
|---|---|
| Scoring API | Stateless FastAPI containers behind a load balancer (Kubernetes/ECS), autoscaled on CPU; the model file is baked into the image, so every replica is identical and versioned |
| Data in | Open-banking consent flow (read-only, purpose-limited, time-limited); transactions fetched per application, not stored beyond the retention the consent allows |
| Audit log | PostgreSQL append-only table or WORM object storage with the same hash chain; daily anchoring of the latest hash |
| Model registry | Each release = data hash + model file + rules version + metrics.json; release gates (tests) block regressions |
| Monitoring | PSI drift, calibration by month, override rate by officer and branch, fairness gaps; alerts to model-risk team |
| Security | API keys → OAuth2/mTLS between bank systems; secrets in a vault; PII never in logs; Georgian data-protection law compliance review |
| Retraining | Quarterly, or when drift/calibration alerts fire; champion–challenger re-run every time |

## What must happen before real customers

1. Pilot in NBG's AI sandbox with one bank or MFI on historical, anonymised data.
2. Train the income model on verified incomes (payroll, Revenue Service data, documents).
3. Add reject inference; validate calibration on real defaults.
4. Independent model validation (NBG model-risk expectations).
5. Confirm with NBG how PTI applies to harvest-shaped schedules; verify every value in `config/nbg_rules.yaml`.
