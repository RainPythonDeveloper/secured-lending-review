# Collateral second opinion

**NBG AI & Open Banking Hackathon 2026 · Track 1: AI in Finance · AI1: Credit Risk & Lending**

One loan application that runs the checks a Georgian loan officer does by hand before a loan is
issued: identity and watchlists, credit history, income from the borrower's consented Open Banking
transactions, affordability under the NBG PTI, maturity and GEL-lending rules, and the collateral
under the LTV limit. The applicant is either one of the 100 customers of the organizer dataset,
whose accounts arrive through the TBC Open Banking sandbox after consent, or a synthetic new
customer. The collateral engine gives an independent second opinion on a Tbilisi flat, private
house or vehicle: comparable sales with a calibrated range, the declared condition read from
photos, a check of the licensed valuer's figure (NBG Order 84/04), and the LTV at the official NBG
exchange rate. Versioned rules, not the language model, set every status; there is no automatic
refusal. The officer decides, and every step is written to a tamper-evident audit log.

> All data is synthetic. No real person, account or bank customer is represented.

## Repository layout

| Path | What | Stack |
|---|---|---|
| `collateral-engine/` | Loan application pipeline (identity, credit history, income, NBG affordability, collateral); valuation of flats, houses and vehicles from comparable sales, condition from photos, appraisal and valuer-report checks, NBG and bank LTV; audit log; officer console | Python, FastAPI, Streamlit |
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
| Platform console: loan application, collateral | http://localhost:8502 |
| Platform API: income, collateral, full application | http://localhost:8100/docs |
| Open Banking gateway (Swagger) | http://localhost:3000/api/docs |

Without Docker, from `collateral-engine/`: `make install`, `make data`, then `make api` and `make app`.
The income engine (`income-engine/`) is installed into the same environment and runs in the same
process; it can still be run on its own, see its README.

The loan application reads accounts through the gateway. Without Docker, start it with
`cd server && npm run start:dev`; approving the consent on the TBC sandbox page is the customer's
step and is done by hand in the demo. If the gateway is down, the console falls back to the bank's
records from `data/`.

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
