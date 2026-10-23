# Collateral second opinion

**NBG AI & Open Banking Hackathon 2026 · Track 1: AI in Finance · AI1: Credit Risk & Lending**

Collateral valuation in Georgia is manual, infrequent and inconsistent between banks. This project
gives the loan officer an independent second opinion on a Tbilisi flat or private house offered as
collateral: comparable sales with a calibrated range, the declared condition read from interior
photos, a check of the licensed valuer's figure against the market range, and the NBG LTV limit at
the official NBG exchange rate. A valuer's report on any real estate, factories included, is checked
against NBG Order 84/04, and vehicles are valued against the bank's own LTV policy. Versioned rules, not the language model, set every status. The officer decides; every
step is written to a tamper-evident audit log. Income from consented Open Banking data (PTI) comes
from the income engine and shares the same dated NBG rules file.

> All data is synthetic. No real person, account or bank customer is represented.

## Repository layout

| Path | What | Stack |
|---|---|---|
| `collateral-engine/` | Valuation of flats, houses and vehicles from comparable sales, condition from photos, appraisal and valuer-report checks, NBG and bank LTV, audit log, officer console | Python, FastAPI, Streamlit |
| `server/` | Open Banking AIS gateway to the TBC mock sandbox (consents with OAuth/PKCE, accounts, balances, transactions); also serves organizer dataset personas through the same endpoints, marked by `X-Data-Source` | NestJS, TypeScript |
| `income-engine/` | Income estimation from transactions, NBG PTI/LTV rules, explainable risk model, audit log, officer console | Python, FastAPI, Streamlit |
| `data/` | Organizer-provided synthetic dataset: 100 customers, 6 months of transactions | XLSX |
| `CLAUDE.md` | Engineering rules for everyone writing code here, human or AI | |

## Run everything

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Open Banking gateway (Swagger) | http://localhost:3000/api/docs |
| Income engine API | http://localhost:8000/docs |
| Officer console (income) | http://localhost:8501 |
| Collateral engine API | http://localhost:8100/docs |
| Collateral console | http://localhost:8502 |

The gateway gets its settings from `docker-compose.yml`, reads the organizer workbook from `data/`
(mounted read-only) and listens on `127.0.0.1` only. To run it without Docker, copy
`server/.env.example` to `server/.env` first; see [`server/README.md`](server/README.md).

Each component's README covers local development:
[`collateral-engine/README.md`](collateral-engine/README.md), [`server/README.md`](server/README.md),
[`income-engine/README.md`](income-engine/README.md).

## External services

- NBG official exchange rates: https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/

- TBC Open Banking sandbox (mock): https://tbc-bank-mock-open-banking-api.vercel.app/reference/aisapioverview
- Sandbox status: https://tbc-bank-status.vercel.app/
