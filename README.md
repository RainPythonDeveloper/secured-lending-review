# Virtual Field Visit

**NBG AI & Open Banking Hackathon 2026 · Track 1: AI in Finance · AI1: Credit Risk & Lending**

Banks must confirm the occupation and income of borrowers without documented income, today by visiting
them on site (NBG Order 44/04). Virtual Field Visit replaces the trip with a recorded video call: an AI
interviewer follows a profession-specific playbook, asks the borrower to show verifiable evidence, and
builds a claim-by-claim report. Versioned rules, not the language model, set each claim's status. The loan
officer makes the decision; every step is written to a tamper-evident audit log.

> All data is synthetic. No real person, account or bank customer is represented.

## Repository layout

| Path | What | Stack |
|---|---|---|
| `server/` | Open Banking AIS gateway to the TBC mock sandbox (consents with OAuth/PKCE, accounts, balances, transactions); also serves organizer dataset personas through the same endpoints, marked by `X-Data-Source` | NestJS, TypeScript |
| `income-engine/` | Income estimation from transactions, NBG PTI/LTV rules, explainable risk model, audit log, officer console | Python, FastAPI, Streamlit |
| `data/` | Organizer-provided synthetic dataset: 100 customers, 6 months of transactions | XLSX |
| `CLAUDE.md` | Engineering rules for everyone writing code here, human or AI | |

Planned: `video-agent/` (real-time interviewer), `judge/` (evidence verification), `borrower-web/` (call UI).

## Run everything

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Open Banking gateway (Swagger) | http://localhost:3000/api/docs |
| Income engine API | http://localhost:8000/docs |
| Officer console | http://localhost:8501 |

The gateway gets its settings from `docker-compose.yml`, reads the organizer workbook from `data/`
(mounted read-only) and listens on `127.0.0.1` only. To run it without Docker, copy
`server/.env.example` to `server/.env` first; see [`server/README.md`](server/README.md).

Each component's README covers local development: [`server/README.md`](server/README.md),
[`income-engine/README.md`](income-engine/README.md).

## External services

- TBC Open Banking sandbox (mock): https://tbc-bank-mock-open-banking-api.vercel.app/reference/aisapioverview
- Sandbox status: https://tbc-bank-status.vercel.app/
