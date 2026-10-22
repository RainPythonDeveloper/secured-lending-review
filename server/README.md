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

Swagger UI: http://localhost:3000/api/docs

## Run

```bash
npm ci
cp .env.example .env
npm run start:dev      # http://localhost:3000
```
Every environment variable is described in `.env.example`. The gateway refuses to start and lists
each missing or invalid variable.

With Docker, from the repository root: `docker compose up --build open-banking-gateway`.

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run test:e2e
npm run build
```
