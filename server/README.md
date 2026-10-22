# Open Banking gateway

NestJS service between our application and the TBC Open Banking sandbox
(Berlin Group NextGenPSD2-based Georgian standard). It exposes the Account Information Service (AIS)
endpoints our pipeline needs and hides OAuth, consent handling and sandbox failures from the callers.

- Sandbox API reference: https://tbc-bank-mock-open-banking-api.vercel.app/reference/aisapioverview
- Sandbox OpenAPI spec (source of truth for field names): https://tbc-bank-mock-open-banking-api.vercel.app/openapi.json
- Sandbox status: https://tbc-bank-status.vercel.app/

## Endpoints

| Method | Path | Upstream |
|---|---|---|
| GET | `/health` | – |
| GET | `/oauth/callback` | `POST /openbanking/oauth/token` (authorization code + PKCE) |
| POST | `/v1/consents` | `POST /0.8/v1/consents`; optional `PSU-ID` header binds an organizer dataset persona |
| GET | `/v1/consents/{consentId}` | `GET /0.8/v1/consents/{consentId}` |
| GET | `/v1/consents/{consentId}/status` | `GET /0.8/v1/consents/{consentId}/status` |
| DELETE | `/v1/consents/{consentId}` | `DELETE /0.8/v1/consents/{consentId}`, then local tokens and binding are forgotten |

Every `/v1/*` success response carries `X-Data-Source` (`tbc-sandbox` or `organizer-dataset`): the
source of the synthetic account data served under that consent.

Swagger UI: http://localhost:3000/api/docs

## Run

```bash
npm ci
cp .env.example .env
npm run start:dev      # http://localhost:3000
```
Every environment variable is described in `.env.example`. The gateway refuses to start and lists
each missing or invalid variable. At startup it reads the synthetic organizer dataset from
`DATASET_XLSX_PATH` (`../data/open-banking-synthetic-100-customers.xlsx`) and refuses to start if a
row is malformed or an account does not reconcile.

With Docker, from the repository root: `docker compose up --build open-banking-gateway`.

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run test:e2e
npm run build
```
