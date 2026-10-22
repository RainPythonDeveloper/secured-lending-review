# Open Banking AIS gateway

NestJS service between our application and the TBC Bank mock Open Banking sandbox (Georgian
standard, based on Berlin Group NextGenPSD2). It exposes the Account Information Service (AIS)
endpoints our pipeline needs (consents, accounts, balances, transactions) with the field and header
names of the TBC specification, and hides OAuth with PKCE, token refresh and sandbox failures from
the callers.

The same endpoints can also serve personas from the hackathon organizer dataset, so that the income
engine sees six months of realistic transactions while the consent itself still goes through the
real sandbox journey: consent creation, the bank consent screen and the OAuth callback.

- Sandbox API reference: https://tbc-bank-mock-open-banking-api.vercel.app/reference/aisapioverview
- Sandbox OpenAPI spec (source of truth for field names): https://tbc-bank-mock-open-banking-api.vercel.app/openapi.json
- Sandbox status: https://tbc-bank-status.vercel.app/
- Swagger UI of this gateway: http://localhost:3000/api/docs (JSON: `/api/docs-json`)

## Data provenance

All data is synthetic. No real person, account or bank customer is represented.

| `X-Data-Source` | Where the account data comes from |
|---|---|
| `tbc-sandbox` | The TBC mock sandbox (its single demo customer and accounts `acc-gel-001`, `acc-usd-002`) |
| `organizer-dataset` | The organizer workbook `data/open-banking-synthetic-100-customers.xlsx`, read at startup |

Every `/v1/*` success response carries `X-Data-Source`. On accounts, balances and transactions it
names the source of that body. On consent endpoints it names the source of the account data served
under the consent; the consent record itself always comes from the sandbox.

Persona binding: `POST /v1/consents` takes an optional `PSU-ID` header. If it names a customer of
the organizer dataset (for example `CUS-024`), the gateway still creates the consent at the sandbox
(forwarding `PSU-ID`, which the spec defines and the sandbox ignores), runs the bank consent screen
and the OAuth flow, and remembers `consentId → customerId`. Without `PSU-ID`, or with an id that is
not in the dataset, the consent serves sandbox data. `psuMessage` in the response says which one
was chosen. For persona consents the gateway reads the consent at the bank on every request and
enforces its status and access scope the way the sandbox does.

Caveat: the bank consent screen always shows the sandbox demo customer, not the persona, because the
sandbox has only one PSU.

## Quick start

Local (Node 24):

```bash
npm ci
cp .env.example .env
npm run start:dev      # http://localhost:3000
```

Docker, from the repository root (publishes the port on `127.0.0.1` and mounts `data/` read-only):

```bash
docker compose up --build open-banking-gateway
```

The gateway refuses to start and lists each missing or invalid variable. At startup it loads the
organizer dataset from `DATASET_XLSX_PATH` and refuses to start if a row is malformed or an
account does not reconcile.

## Walkthrough with curl

```bash
VALID_UNTIL=$(date -v+30d +%F)          # GNU date: date -d '+30 days' +%F
curl -sS -i -X POST http://localhost:3000/v1/consents \
  -H 'Content-Type: application/json' -H 'PSU-ID: CUS-024' \
  -d '{"access":{"accounts":[],"balances":[],"transactions":[]},"recurringIndicator":true,"validUntil":"'"$VALID_UNTIL"'","frequencyPerDay":4,"combinedServiceIndicator":false}'
```

1. The 201 response has `consentId`, `consentStatus: "received"`, `psuMessage` and
   `_links.scaRedirect.href`, the bank authorisation URL. Leave out `PSU-ID` to get sandbox data.
2. Open `scaRedirect.href` in a browser and press approve on the bank page.
3. The bank redirects to `http://localhost:3000/oauth/callback?state=…&code=…`. The gateway
   exchanges the code (PKCE) and answers `{"consentId":"…","scaStatus":"finalised"}`. Tokens stay
   inside the gateway.
4. Read data with the consent:

```bash
CONSENT_ID=<consentId from step 1>
curl -sS -i 'http://localhost:3000/v1/accounts?withBalance=true' -H "Consent-ID: $CONSENT_ID"
curl -sS -i http://localhost:3000/v1/accounts/ACC-0024/balances -H "Consent-ID: $CONSENT_ID"
curl -sS -i 'http://localhost:3000/v1/accounts/ACC-0024/transactions?dateFrom=2026-04-20&dateTo=2026-10-19' \
  -H "Consent-ID: $CONSENT_ID"
curl -sS -i -X DELETE http://localhost:3000/v1/consents/$CONSENT_ID
```

For a sandbox consent use the account ids `acc-gel-001` or `acc-usd-002`.

## Configuration

Every variable is validated at startup and documented in `.env.example`, which carries working
values. The gateway has no secrets: the sandbox uses a public OAuth client without a client secret.

| Variable | Default | `.env.example` | Rule |
|---|---|---|---|
| `PORT` | 3000 | 3000 | integer 1–65535 |
| `TBC_API_BASE_URL` | required | `https://tbc-bank-mock-open-banking-api.vercel.app/0.8` | http(s) URL, trailing `/` stripped |
| `TBC_OAUTH_AUTHORIZE_URL` | required | `https://tbc-bank-mock-open-banking-api.vercel.app/psd2/openbanking/oauth/authorize` | URL |
| `TBC_OAUTH_TOKEN_URL` | required | `https://tbc-bank-mock-open-banking-api.vercel.app/openbanking/oauth/token` | URL |
| `TBC_OAUTH_CLIENT_ID` | required | `virtual-field-visit-gateway` | 1–128 characters |
| `TBC_OAUTH_REDIRECT_URI` | required | `http://localhost:3000/oauth/callback` | URL; sent as `TPP-Redirect-URI` and `redirect_uri`, the sandbox requires both to match |
| `TBC_OAUTH_UI_LOCALE` | `en` | `en` | `en` or `ka` |
| `TBC_HTTP_TIMEOUT_MS` | 8000 | 8000 | integer 100–60000, per attempt |
| `TBC_RETRY_MAX_ATTEMPTS` | 3 | 3 | integer 1–3, GET only, first attempt included |
| `TBC_RETRY_BASE_DELAY_MS` | 250 | 250 | integer 0–10000 |
| `TBC_RETRY_MAX_DELAY_MS` | 2000 | 2000 | integer 0–30000, not below the base delay |
| `OAUTH_STATE_TTL_MS` | 600000 | 600000 | integer 10000–3600000, lifetime of a pending OAuth state |
| `OAUTH_TOKEN_REFRESH_MARGIN_MS` | 60000 | 60000 | integer 0–600000, refresh this long before expiry |
| `DATASET_XLSX_PATH` | required | `../data/open-banking-synthetic-100-customers.xlsx` | relative paths resolve against the working directory; Docker uses `/app/data/open-banking-synthetic-100-customers.xlsx` |

## Endpoints

Every response carries `X-Request-ID`: the caller's value if it is a UUID, otherwise a generated
one. Optional caller headers on `/v1/*`: `PSU-IP-Address` (defaults to the caller IP) and
`X-Request-ID`.

| Method | Path | Caller input | Success | Upstream |
|---|---|---|---|---|
| GET | `/health` | – | 200 `{"status":"ok"}` | – |
| POST | `/v1/consents` | `PSU-ID`?, body `access`, `recurringIndicator`, `validUntil`, `frequencyPerDay` (1–4), `combinedServiceIndicator` | 201 + `X-Data-Source` | `POST /0.8/v1/consents` |
| GET | `/v1/consents/{consentId}` | – | 200 + `X-Data-Source` | `GET /0.8/v1/consents/{consentId}` |
| GET | `/v1/consents/{consentId}/status` | – | 200 + `X-Data-Source` | `GET /0.8/v1/consents/{consentId}/status` |
| DELETE | `/v1/consents/{consentId}` | – | 204 + `X-Data-Source` | `DELETE /0.8/v1/consents/{consentId}`, then local tokens, binding and pending states are forgotten |
| GET | `/oauth/callback` | `state`, `code` or `error` (set by the bank redirect) | 200 `{consentId, scaStatus: "finalised"}` | `POST /openbanking/oauth/token` (authorization code + PKCE) |
| GET | `/v1/accounts` | `Consent-ID`, `withBalance=true\|false` | 200 + `X-Data-Source` | `GET /0.8/v1/accounts` or the dataset |
| GET | `/v1/accounts/{accountId}` | `Consent-ID`, `withBalance` | 200 + `X-Data-Source` | `GET /0.8/v1/accounts/{accountId}` or the dataset |
| GET | `/v1/accounts/{accountId}/balances` | `Consent-ID` | 200 + `X-Data-Source` | `GET /0.8/v1/accounts/{accountId}/balances` or the dataset |
| GET | `/v1/accounts/{accountId}/transactions` | `Consent-ID`, `dateFrom`?, `dateTo`?, `bookingStatus`? | 200 + `X-Data-Source` | `GET /0.8/v1/accounts/{accountId}/transactions` or the dataset |
| GET | `/api/docs`, `/api/docs-json` | – | Swagger UI / OpenAPI JSON | – |

Account endpoints need the `Consent-ID` (UUID) of a consent authorised through `/oauth/callback`.
`dateFrom` and `dateTo` are inclusive ISO dates with `dateFrom ≤ dateTo`; `bookingStatus` is
`booked` (default), `pending` or `both`. Amounts are decimal strings (`"3247.50"`), never numbers.
Links in `_links` point at gateway routes, not at sandbox paths.

## Errors

Errors use the sandbox format: `Content-Type: application/problem+json; charset=utf-8`, body
`{type: "about:blank", title, status, code, detail, tppMessages: [{category: "ERROR", code, text}]}`.

| Situation | Status | `code` |
|---|---|---|
| Invalid body, query, path parameter or header | 400 | `FORMAT_ERROR` |
| Unknown route | 404 | `RESOURCE_UNKNOWN` |
| OAuth `state` unknown, expired or already used | 400 | `STATE_INVALID` |
| PSU denied the consent at the bank | 403 | `ACCESS_DENIED` |
| Consent never authorised through the gateway, or token refresh rejected | 401 | `TOKEN_INVALID` |
| Sandbox problem+json 4xx | same status | sandbox `code` (`CONSENT_UNKNOWN`, `CONSENT_INVALID`, `TOKEN_INVALID`, …) |
| Sandbox OAuth error 4xx | same status | upper-cased OAuth `error` (`INVALID_GRANT`, …) |
| Sandbox 5xx (after retries for GET) | 502 | sandbox `code` or `SERVICE_UNAVAILABLE`; `detail` ends with `(after N attempts)` |
| Sandbox unreachable | 502 | `SERVICE_UNAVAILABLE` |
| Sandbox timeout (after retries for GET) | 504 | `UPSTREAM_TIMEOUT` |
| Sandbox payload does not match the specification | 502 | `UPSTREAM_CONTRACT_VIOLATION` |
| Persona consent not `valid` / outside its access scope / unknown account | 401 / 403 / 404 | `CONSENT_INVALID` / `CONSENT_INVALID` / `RESOURCE_UNKNOWN` |
| Anything else | 500 | `INTERNAL_ERROR` (generic detail; the error is logged, the stack is never sent) |

## Architecture

```
caller ──HTTP──► controllers (ais/consents, ais/accounts, ais/balances, ais/transactions, oauth, health)
                   │
                   ▼
                 services ──► AisProviderResolver ── PersonaBindingStore (consentId → customerId)
                                 │
                 ┌───────────────┴────────────────┐
                 ▼                                ▼
        SandboxAisProvider                 DatasetAisProvider ──► OrganizerDataset ◄── xlsx (read at startup)
                 │                                │ (consent status and access read at the bank)
                 ▼                                ▼
            OAuthService ◄── ConsentTokenStore, PendingAuthorisationStore (in memory)
                 │
                 ▼
         tbc-client (TbcClientService → TbcHttpTransport: timeout, GET retries, X-Request-ID)
                 │
                 ▼
          TBC mock sandbox
```

Cross-cutting, in `src/common/`: problem+json filter, `X-Request-ID` middleware, `X-Data-Source`
interceptor, header parsers and Swagger setup. Configuration is read and validated only in
`src/config/`.

## Organizer dataset mapping

Only `current` accounts are exposed through v1 AIS; TBC serves savings and deposits through the v2
API, which is out of scope. Transfers to savings stay visible through the counterparty IBAN.

| AIS field | Source | Rule |
|---|---|---|
| `resourceId` | `Accounts.account_id` | as is (`ACC-0024`) |
| `iban` | `account_id` | synthetic IBAN, see below |
| `currency` | `Accounts.currency` | as is |
| `name` | `account_type` | constant `"Current account"` |
| `ownerName` | `Customers.full_name` | as is |
| `cashAccountType` / `usage` | – | constants `CACC` / `PRIV` |
| `status` | `Accounts.status` | `active` → `enabled`, `closed` → `deleted` |
| `bic`, `displayName`, `product` | – | omitted (no synthetic BIC is invented) |
| `balances` | `closing_balance` | `interimBooked` and `interimAvailable` (the dataset defines available = booked on current accounts), `creditLimitIncluded: false`, `referenceDate` = last booking date of the dataset (2026-10-19) |
| `transactionId` | `transaction_id` | as is |
| `entryReference` | `posting_sequence` | decimal string |
| `endToEndId` | `transfer_id` | only when present (same value on both legs) |
| `bookingDate`, `valueDate` | `booking_date` | ISO date (the dataset has no separate value date) |
| `transactionAmount` | `currency`, `amount` | `{currency, amount}`, signed decimal string |
| `debtorName` / `creditorName` | `counterparty` | amount > 0 → `debtorName` (payer); amount < 0 → `creditorName` (payee) |
| `debtorAccount` / `creditorAccount` | `related_account_id` | internal and FX transfers only: `{iban, currency}` of the related account on the counterparty side |
| `remittanceInformationUnstructured` | `description` | as is |
| `additionalInformation` | `channel` | as is (`cash`, `card`, `bank_transfer`, …) |
| `proprietaryBankTransactionCode` | `category` | as is (dataset vocabulary, for example `business_income`) |
| `currencyExchange` | `fx_rate` | only when present: `[{sourceCurrency, exchangeRate, unitCurrency: sourceCurrency, targetCurrency, quotationDate: bookingDate}]`; the debit leg converts from its own currency, the credit leg into it |
| `balanceAfterTransaction` | `balance_after` | `{balanceType: "interimBooked", balanceAmount}` |
| not mapped | `customer_id`, `refund_of_id`, customer age/city/profile/household/income, Deposits, DailyBalances, Reconciliation | no spec field or out of scope |

Synthetic IBAN: `GE` + ISO 13616 mod-97 check digits + bank code `XX` + the account number from
`ACC-NNNN` zero-padded to 16 digits. No Georgian bank uses `XX`, so the IBANs are recognisably
synthetic, yet they pass mod-97 validators. Examples: `ACC-0024` → `GE38XX0000000000000024`,
`ACC-0011` → `GE98XX0000000000000011`.

Amounts: the workbook is read with numbers kept as their exact text, parsed into integer minor units
(`"-39.86"` → `-3986`) and formatted back with integer arithmetic only (`350000` → `"3500.00"`).
There is no floating-point step. At startup the loader checks that opening balance + Σ amounts =
closing balance for every account.

## Retries and timeouts

- Each sandbox attempt has its own timeout, `TBC_HTTP_TIMEOUT_MS` (8 s: above the sandbox's very-slow
  tier of up to 7 s, below its timeout-prone tier of 10–15 s).
- Only GET requests are retried, and only after a 5xx or a timeout, with at most
  `TBC_RETRY_MAX_ATTEMPTS` attempts in total. Consent creation, token calls and DELETE are never
  retried; neither are 4xx responses or connection errors.
- Backoff is exponential with equal jitter: before retry *n* the gateway waits between half and all
  of `min(TBC_RETRY_MAX_DELAY_MS, TBC_RETRY_BASE_DELAY_MS · 2^(n-1))`, by default 125–250 ms, then
  250–500 ms.
- Every attempt sends a new UUID v4 `X-Request-ID` and writes one log line: operation, attempt k/N,
  upstream and gateway request ids, status or timeout, duration. Headers, tokens, bodies, query
  strings and path ids are never logged.
- Access tokens are refreshed with the refresh token `OAUTH_TOKEN_REFRESH_MARGIN_MS` before they
  expire, one refresh at a time per consent.

## Guardrails in code

| Guardrail | Where |
|---|---|
| Tokens are never returned or logged | `src/oauth/consent-token.store.ts`, `src/oauth/oauth.controller.ts`, `src/tbc-client/tbc-http-transport.ts` |
| Only idempotent GETs are retried, only after 5xx or timeout | `src/tbc-client/retry-policy.ts` |
| Errors are problem+json, stacks are never sent | `src/common/problem-details/` |
| Input is validated at the boundary | DTOs under `src/**/dto/`, `src/common/request-context/request-headers.ts` |
| Sandbox payloads are validated against the spec DTOs | `src/tbc-client/upstream-payload.ts` |
| Persona consents obey the bank's consent status and access scope | `src/ais/providers/dataset/` |
| Dataset rows and balances are checked at startup | `src/organizer-dataset/organizer-dataset.ts`, `src/organizer-dataset/dataset-row-parsers.ts` |
| Amounts never pass through floating point | `src/organizer-dataset/minor-units.ts` |
| Data provenance is visible on every response | `src/common/data-source/` |
| Configuration is validated at startup | `src/config/` |

## Limitations

- Tokens, PKCE verifiers and persona bindings live in memory: a restart loses them and consents must
  be authorised again. Run a single instance.
- Callers are not authenticated: a `Consent-ID` acts as a capability for the data of that consent.
  Run the gateway on localhost or a private network; Docker Compose publishes it on `127.0.0.1` only.
- The bank consent screen shows the sandbox demo customer, also for persona consents.
- The sandbox injects random 5xx responses and delays, and sometimes reports a valid consent as
  expired (401 `CONSENT_INVALID` "Consent is expired"). The gateway retries GETs and passes the rest
  through as problem+json; create a new consent when a consent expires.
- Only v1 AIS (current accounts) is covered; savings, deposits and payments are out of scope.

## Tests

```bash
npm run lint
npm run typecheck
npm test               # unit tests next to the code, no network
npm run test:e2e       # supertest against the full app with a fake sandbox client, no network
npm run build
```

Opt-in live smoke test against the real TBC sandbox (needs a running gateway and `.env`; not part of
`npm test` or CI): `npm run smoke:sandbox`. It creates a sandbox consent and a persona consent
(`SMOKE_PERSONA_ID`, default `CUS-024`), approves both on the mock bank page like a PSU would, reads
accounts, balances and transactions, checks the problem+json passthrough of sandbox 404 and 401
errors, and deletes every consent it created. `SMOKE_GATEWAY_URL` defaults to
`http://localhost:3000`. If an injected sandbox failure hits a step, run it again.

## Third-party components

Licences as declared in each package's `package.json` (installed versions).

| Component | Version | Licence | Used for |
|---|---|---|---|
| `@nestjs/common`, `@nestjs/core`, `@nestjs/platform-express` | 12.2.0 | MIT | HTTP framework |
| `@nestjs/swagger` | 12.0.2 | MIT | OpenAPI document |
| `swagger-ui-express` | 5.0.1 | MIT | Swagger UI |
| `class-validator` | 0.15.1 | MIT | DTO validation |
| `class-transformer` | 0.5.1 | MIT | DTO transformation |
| `read-excel-file` | 9.3.12 | MIT | Reading the organizer workbook |
| `fflate`, `saxen`, `unzipper-esm`, `worker-f` | 0.8.3, 11.2.0, 0.13.3, 0.1.20 | MIT | Dependencies of `read-excel-file` |
| `reflect-metadata` | 0.2.2 | Apache-2.0 | Decorator metadata |
| `rxjs` | 7.8.2 | Apache-2.0 | NestJS interceptors |
| `typescript` (dev) | 6.0.3 | Apache-2.0 | Compiler and type check |
| `vitest`, `@vitest/coverage-v8` (dev) | 4.1.12 | MIT | Test runner, coverage |
| `vite` (dev) | 8.3.5 | MIT | Test transform |
| `supertest` (dev) | 7.3.1 | MIT | E2E HTTP tests |
| `oxlint` (dev) | 1.89.0 | MIT | Linter |
| `oxlint-tsgolint` (dev) | 7.0.2004 | MIT | Type-aware lint rules |
| `prettier` (dev) | 3.9.10 | MIT | Formatter |
| `@nestjs/cli`, `@nestjs/schematics` (dev) | 12.0.10 | MIT | Build tooling |
| `@nestjs/testing` (dev) | 12.2.0 | MIT | Test module |
| `@nestjs/mau` (dev) | 0.2.8 | MIT | NestJS deploy tooling (`npm run deploy`) |
| `@types/express`, `@types/node`, `@types/supertest` (dev) | 5.0.6, 24.19.2, 7.2.1 | MIT | Type definitions |
| `source-map-support` (dev) | 0.5.21 | MIT | Stack traces in development |
| TBC Bank mock Open Banking sandbox | API 0.8 | provided by the hackathon organizers | Consents, OAuth, sandbox account data |
| Organizer dataset `data/open-banking-synthetic-100-customers.xlsx` | – | provided by the hackathon organizers, synthetic | Persona account data |

This gateway is released under the MIT licence of the repository (`../LICENSE`).
