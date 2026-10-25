// Opt-in live check of a running gateway against the real TBC sandbox. It is kept out of
// vitest and CI on purpose: the sandbox injects failures and the run creates real consents.
// Self-contained and erasable-only TypeScript so that Node runs it with type stripping.
import { randomUUID } from 'node:crypto';

type JsonRecord = Record<string, unknown>;
type DataSource = 'tbc-sandbox' | 'organizer-dataset';
type ConsentKind = 'sandbox' | 'persona';
type StepOutcome = 'PASS' | 'FAIL';

interface SmokeSettings {
  readonly gatewayUrl: string;
  readonly sandboxApiBaseUrl: string;
  readonly personaId: string;
}

interface JsonResponse {
  readonly status: number;
  readonly headers: Headers;
  readonly body: unknown;
}

interface CreatedConsent {
  readonly kind: ConsentKind;
  readonly consentId: string;
}

interface PendingConsent {
  readonly consentId: string;
  readonly scaRedirectHref: string;
}

interface SmokeStep {
  readonly name: string;
  readonly run: () => Promise<string>;
}

interface BookedTransaction {
  readonly bookingDate: string;
  readonly amountMinorUnits: number;
  readonly currency: string;
  readonly proprietaryBankTransactionCode: string | undefined;
}

const DEFAULT_GATEWAY_URL = 'http://localhost:3000';
const DEFAULT_PERSONA_ID = 'CUS-024';
const CONSENT_VALIDITY_DAYS = 30;
const CONSENT_FREQUENCY_PER_DAY = 4;
const MS_PER_DAY = 86_400_000;
const ISO_DATE_LENGTH = 10;
const YEAR_MONTH_LENGTH = 7;
const MINOR_UNITS_PER_MAJOR_UNIT = 100;
const MINOR_UNIT_DIGITS = 2;
const DATASET_PERIOD = { dateFrom: '2026-04-20', dateTo: '2026-10-19' };
// Counted in the organizer workbook; accounts of other personas get the generic checks only.
const EXPECTED_BOOKED_COUNT_BY_ACCOUNT_ID: ReadonlyMap<string, number> =
  new Map([['ACC-0024', 284]]);
const AMOUNT_TEXT_PATTERN = /^(-?)(\d+)\.(\d{2})$/;
const SYNTHETIC_IBAN_PATTERN = /^GE\d{2}XX\d{16}$/;
const TRAILING_SLASHES_PATTERN = /\/+$/;
const BUSINESS_INCOME_TRANSACTION_CODE = 'business_income';
const DATA_SOURCE_HEADER = 'X-Data-Source';
const DATA_SOURCE_BY_CONSENT_KIND: Readonly<Record<ConsentKind, DataSource>> = {
  sandbox: 'tbc-sandbox',
  persona: 'organizer-dataset',
};
const JSON_MEDIA_TYPE = 'application/json';
const PROBLEM_JSON_MEDIA_TYPE = 'application/problem+json';
const FORM_MEDIA_TYPE = 'application/x-www-form-urlencoded';
const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  UNAUTHORIZED: 401,
  NOT_FOUND: 404,
} as const;
const REDIRECT_STATUSES: ReadonlySet<number> = new Set([
  301, 302, 303, 307, 308,
]);

function readSettings(environment: NodeJS.ProcessEnv): SmokeSettings {
  const sandboxApiBaseUrl = environment.TBC_API_BASE_URL;
  if (sandboxApiBaseUrl === undefined || sandboxApiBaseUrl === '') {
    throw new Error(
      'TBC_API_BASE_URL is not set; run `npm run smoke:sandbox` so that server/.env is loaded',
    );
  }
  return {
    gatewayUrl: stripTrailingSlashes(
      environment.SMOKE_GATEWAY_URL ?? DEFAULT_GATEWAY_URL,
    ),
    sandboxApiBaseUrl: stripTrailingSlashes(sandboxApiBaseUrl),
    personaId: environment.SMOKE_PERSONA_ID ?? DEFAULT_PERSONA_ID,
  };
}

function stripTrailingSlashes(url: string): string {
  return url.replace(TRAILING_SLASHES_PATTERN, '');
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readPath(value: unknown, path: string): unknown {
  let current = value;
  for (const fieldName of path.split('.')) {
    if (!isJsonRecord(current)) {
      throw new Error(`expected an object on the way to "${path}"`);
    }
    current = current[fieldName];
  }
  return current;
}

function readString(value: unknown, path: string): string {
  const field = readPath(value, path);
  if (typeof field !== 'string') {
    throw new Error(`expected a string at "${path}"`);
  }
  return field;
}

function readOptionalString(value: unknown, path: string): string | undefined {
  return readPath(value, path) === undefined
    ? undefined
    : readString(value, path);
}

function readNonEmptyArray(value: unknown, path: string): unknown[] {
  const field = readPath(value, path);
  if (!Array.isArray(field) || field.length === 0) {
    throw new Error(`expected a non-empty array at "${path}"`);
  }
  return field;
}

function readArray(value: unknown, path: string): unknown[] {
  const field = readPath(value, path);
  if (!Array.isArray(field)) {
    throw new Error(`expected an array at "${path}"`);
  }
  return field;
}

async function requestJson(
  url: string,
  init: RequestInit = {},
): Promise<JsonResponse> {
  const response = await fetch(url, { ...init, redirect: 'manual' });
  const bodyText = await response.text();
  return {
    status: response.status,
    headers: response.headers,
    body: parseJsonBody(bodyText, response.status, url),
  };
}

function parseJsonBody(bodyText: string, status: number, url: string): unknown {
  if (bodyText === '') {
    return undefined;
  }
  try {
    return JSON.parse(bodyText);
  } catch (error) {
    throw new Error(
      `${new URL(url).pathname} answered ${status} with a body that is not JSON`,
      { cause: error },
    );
  }
}

async function readRedirectLocation(
  url: string,
  init: RequestInit = {},
): Promise<URL> {
  const response = await fetch(url, { ...init, redirect: 'manual' });
  await response.body?.cancel();
  const location = response.headers.get('location');
  if (!REDIRECT_STATUSES.has(response.status) || location === null) {
    throw new Error(
      `expected a redirect from ${new URL(url).pathname}, got ${response.status}`,
    );
  }
  return new URL(location, url);
}

// Plays the PSU on the mock bank page. Only this test tooling does it; the gateway never
// approves consents on behalf of a PSU.
async function approveLikePsu(
  settings: SmokeSettings,
  scaRedirectHref: string,
): Promise<JsonResponse> {
  const bankPageUrl = await readRedirectLocation(scaRedirectHref);
  const redirectBackUrl = await readRedirectLocation(bankPageUrl.href, {
    method: 'POST',
    headers: { 'Content-Type': FORM_MEDIA_TYPE },
    body: new URLSearchParams({ decision: 'approve' }).toString(),
  });
  return requestJson(
    `${settings.gatewayUrl}/oauth/callback${redirectBackUrl.search}`,
  );
}

function describeProblemBody(body: unknown): string {
  if (!isJsonRecord(body) || typeof body.code !== 'string') {
    return '';
  }
  return typeof body.detail === 'string'
    ? ` ${body.code} "${body.detail}"`
    : ` ${body.code}`;
}

function assertStatus(
  response: JsonResponse,
  expectedStatus: number,
  requestDescription: string,
): void {
  if (response.status !== expectedStatus) {
    throw new Error(
      `${requestDescription} answered ${response.status}${describeProblemBody(response.body)}, expected ${expectedStatus}`,
    );
  }
}

function assertEqual(
  actual: unknown,
  expected: unknown,
  valueDescription: string,
): void {
  if (actual !== expected) {
    throw new Error(
      `${valueDescription} is ${String(actual)}, expected ${String(expected)}`,
    );
  }
}

function assertDataSource(response: JsonResponse, expected: DataSource): void {
  assertEqual(
    response.headers.get(DATA_SOURCE_HEADER),
    expected,
    DATA_SOURCE_HEADER,
  );
}

function assertProblem(
  response: JsonResponse,
  expectedStatus: number,
  expectedCode: string,
): string {
  assertStatus(response, expectedStatus, `request expecting ${expectedCode}`);
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.startsWith(PROBLEM_JSON_MEDIA_TYPE)) {
    throw new Error(
      `expected ${PROBLEM_JSON_MEDIA_TYPE}, got "${contentType}"`,
    );
  }
  assertEqual(readString(response.body, 'code'), expectedCode, 'problem code');
  assertEqual(readPath(response.body, 'status'), expectedStatus, 'status');
  readNonEmptyArray(response.body, 'tppMessages');
  return `${expectedStatus} ${expectedCode} problem+json "${readString(response.body, 'detail')}"`;
}

function parseAmountToMinorUnits(amountText: string): number {
  const match = AMOUNT_TEXT_PATTERN.exec(amountText);
  if (match === null) {
    throw new Error(
      `amount "${amountText}" is not a decimal string with 2 decimals`,
    );
  }
  const [, sign, units, fraction] = match;
  const absoluteMinorUnits =
    Number(units) * MINOR_UNITS_PER_MAJOR_UNIT + Number(fraction);
  return sign === '-' ? -absoluteMinorUnits : absoluteMinorUnits;
}

function formatMinorUnits(amountMinorUnits: number): string {
  const sign = amountMinorUnits < 0 ? '-' : '';
  const absoluteMinorUnits = Math.abs(amountMinorUnits);
  const units = Math.trunc(absoluteMinorUnits / MINOR_UNITS_PER_MAJOR_UNIT);
  const fraction = String(absoluteMinorUnits % MINOR_UNITS_PER_MAJOR_UNIT);
  return `${sign}${units}.${fraction.padStart(MINOR_UNIT_DIGITS, '0')}`;
}

function assertAmountTexts(amountTexts: readonly string[]): void {
  for (const amountText of amountTexts) {
    parseAmountToMinorUnits(amountText);
  }
}

function readBalanceAmounts(balances: readonly unknown[]): string[] {
  return balances.map((balance) => readString(balance, 'balanceAmount.amount'));
}

function describeBalances(balances: readonly unknown[]): string {
  return balances
    .map(
      (balance) =>
        `${readString(balance, 'balanceType')} ${readString(balance, 'balanceAmount.amount')} ${readString(balance, 'balanceAmount.currency')}`,
    )
    .join(', ');
}

function buildBankOfferedConsentRequest(today: Date): JsonRecord {
  const validUntil = new Date(
    today.getTime() + CONSENT_VALIDITY_DAYS * MS_PER_DAY,
  );
  return {
    access: { accounts: [], balances: [], transactions: [] },
    recurringIndicator: true,
    validUntil: validUntil.toISOString().slice(0, ISO_DATE_LENGTH),
    frequencyPerDay: CONSENT_FREQUENCY_PER_DAY,
    combinedServiceIndicator: false,
  };
}

async function createConsent(
  settings: SmokeSettings,
  kind: ConsentKind,
  createdConsents: CreatedConsent[],
): Promise<PendingConsent> {
  const psuHeaders: Record<string, string> =
    kind === 'persona' ? { 'PSU-ID': settings.personaId } : {};
  const response = await requestJson(`${settings.gatewayUrl}/v1/consents`, {
    method: 'POST',
    headers: { 'Content-Type': JSON_MEDIA_TYPE, ...psuHeaders },
    body: JSON.stringify(buildBankOfferedConsentRequest(new Date())),
  });
  assertStatus(response, HTTP_STATUS.CREATED, 'POST /v1/consents');
  const consentId = readString(response.body, 'consentId');
  createdConsents.push({ kind, consentId });
  assertDataSource(response, DATA_SOURCE_BY_CONSENT_KIND[kind]);
  assertEqual(
    readString(response.body, 'consentStatus'),
    'received',
    'consentStatus',
  );
  return {
    consentId,
    scaRedirectHref: readString(response.body, '_links.scaRedirect.href'),
  };
}

async function readConsentStatus(
  settings: SmokeSettings,
  consentId: string,
): Promise<string> {
  const response = await requestJson(
    `${settings.gatewayUrl}/v1/consents/${consentId}/status`,
  );
  assertStatus(response, HTTP_STATUS.OK, 'GET /v1/consents/{consentId}/status');
  return readString(response.body, 'consentStatus');
}

async function authoriseConsent(
  settings: SmokeSettings,
  kind: ConsentKind,
  createdConsents: CreatedConsent[],
): Promise<string> {
  const { consentId, scaRedirectHref } = await createConsent(
    settings,
    kind,
    createdConsents,
  );
  const callback = await approveLikePsu(settings, scaRedirectHref);
  assertStatus(callback, HTTP_STATUS.OK, 'GET /oauth/callback');
  assertEqual(
    readString(callback.body, 'consentId'),
    consentId,
    'callback consentId',
  );
  assertEqual(readString(callback.body, 'scaStatus'), 'finalised', 'scaStatus');
  const consentStatus = await readConsentStatus(settings, consentId);
  assertEqual(consentStatus, 'valid', 'consentStatus after approval');
  return `consent ${consentId} approved at the bank, status ${consentStatus}, ${DATA_SOURCE_HEADER} ${DATA_SOURCE_BY_CONSENT_KIND[kind]}`;
}

function findConsentId(
  createdConsents: readonly CreatedConsent[],
  kind: ConsentKind,
): string {
  const createdConsent = createdConsents.find(
    (consent) => consent.kind === kind,
  );
  if (createdConsent === undefined) {
    throw new Error(`no ${kind} consent was created by an earlier step`);
  }
  return createdConsent.consentId;
}

async function readAisResource(
  settings: SmokeSettings,
  pathAndQuery: string,
  consentId: string,
  expectedDataSource: DataSource,
): Promise<JsonResponse> {
  const response = await requestJson(`${settings.gatewayUrl}${pathAndQuery}`, {
    headers: { 'Consent-ID': consentId },
  });
  assertStatus(
    response,
    HTTP_STATUS.OK,
    `GET ${new URL(pathAndQuery, settings.gatewayUrl).pathname}`,
  );
  assertDataSource(response, expectedDataSource);
  return response;
}

function buildAccountPath(accountId: string, resource: string): string {
  return `/v1/accounts/${encodeURIComponent(accountId)}/${resource}`;
}

async function checkSandboxData(
  settings: SmokeSettings,
  consentId: string,
): Promise<string> {
  const read = (pathAndQuery: string): Promise<JsonResponse> =>
    readAisResource(settings, pathAndQuery, consentId, 'tbc-sandbox');
  const accounts = readNonEmptyArray(
    (await read('/v1/accounts?withBalance=true')).body,
    'accounts',
  );
  assertAmountTexts(
    readBalanceAmounts(
      accounts.flatMap((account) => readArray(account, 'balances')),
    ),
  );
  const accountId = readString(accounts[0], 'resourceId');
  const balances = readNonEmptyArray(
    (await read(buildAccountPath(accountId, 'balances'))).body,
    'balances',
  );
  assertAmountTexts(readBalanceAmounts(balances));
  const transactions = await read(
    `${buildAccountPath(accountId, 'transactions')}?bookingStatus=both`,
  );
  const booked = readArray(transactions.body, 'transactions.booked');
  const pending = readArray(transactions.body, 'transactions.pending');
  assertAmountTexts(
    [...booked, ...pending].map((transaction) =>
      readString(transaction, 'transactionAmount.amount'),
    ),
  );
  return `${accounts.length} accounts; ${accountId} balances ${describeBalances(balances)}; ${booked.length} booked + ${pending.length} pending transactions, amounts are 2-decimal strings`;
}

function readBookedTransaction(transaction: unknown): BookedTransaction {
  return {
    bookingDate: readString(transaction, 'bookingDate'),
    amountMinorUnits: parseAmountToMinorUnits(
      readString(transaction, 'transactionAmount.amount'),
    ),
    currency: readString(transaction, 'transactionAmount.currency'),
    proprietaryBankTransactionCode: readOptionalString(
      transaction,
      'proprietaryBankTransactionCode',
    ),
  };
}

function assertSyntheticIbans(accounts: readonly unknown[]): string[] {
  const ibans = accounts.map((account) => readString(account, 'iban'));
  const nonSyntheticIban = ibans.find(
    (iban) => !SYNTHETIC_IBAN_PATTERN.test(iban),
  );
  if (nonSyntheticIban !== undefined) {
    throw new Error(
      `IBAN ${nonSyntheticIban} does not follow the synthetic GE..XX scheme`,
    );
  }
  return ibans;
}

function assertBookedCount(accountId: string, bookedCount: number): void {
  const expectedCount = EXPECTED_BOOKED_COUNT_BY_ACCOUNT_ID.get(accountId);
  if (expectedCount !== undefined) {
    assertEqual(
      bookedCount,
      expectedCount,
      `booked transactions of ${accountId}`,
    );
  }
}

function assertBookingDatesInPeriod(bookingDates: readonly string[]): void {
  const isAscending = bookingDates.every(
    (bookingDate, index) =>
      index === 0 || bookingDates[index - 1] <= bookingDate,
  );
  const isInPeriod = bookingDates.every(
    (bookingDate) =>
      bookingDate >= DATASET_PERIOD.dateFrom &&
      bookingDate <= DATASET_PERIOD.dateTo,
  );
  if (!isAscending || !isInPeriod) {
    throw new Error(
      `booking dates must be ascending within ${DATASET_PERIOD.dateFrom}..${DATASET_PERIOD.dateTo}`,
    );
  }
}

function describeMonthlyBusinessIncome(
  transactions: readonly BookedTransaction[],
): string {
  const totalMinorUnitsByMonth = new Map<string, number>();
  for (const transaction of transactions) {
    if (
      transaction.proprietaryBankTransactionCode !==
      BUSINESS_INCOME_TRANSACTION_CODE
    ) {
      continue;
    }
    const month = transaction.bookingDate.slice(0, YEAR_MONTH_LENGTH);
    const totalMinorUnits = totalMinorUnitsByMonth.get(month) ?? 0;
    totalMinorUnitsByMonth.set(
      month,
      totalMinorUnits + transaction.amountMinorUnits,
    );
  }
  return [...totalMinorUnitsByMonth]
    .map(
      ([month, totalMinorUnits]) =>
        `${month} ${formatMinorUnits(totalMinorUnits)}`,
    )
    .join(', ');
}

async function checkPersonaData(
  settings: SmokeSettings,
  consentId: string,
): Promise<string> {
  const read = (pathAndQuery: string): Promise<JsonResponse> =>
    readAisResource(settings, pathAndQuery, consentId, 'organizer-dataset');
  const accounts = readNonEmptyArray(
    (await read('/v1/accounts?withBalance=true')).body,
    'accounts',
  );
  const [iban] = assertSyntheticIbans(accounts);
  const accountId = readString(accounts[0], 'resourceId');
  const periodQuery = new URLSearchParams(DATASET_PERIOD).toString();
  const transactions = await read(
    `${buildAccountPath(accountId, 'transactions')}?${periodQuery}`,
  );
  const booked = readNonEmptyArray(
    transactions.body,
    'transactions.booked',
  ).map(readBookedTransaction);
  assertBookedCount(accountId, booked.length);
  const bookingDates = booked.map((transaction) => transaction.bookingDate);
  assertBookingDatesInPeriod(bookingDates);
  return `${settings.personaId} ${accountId} ${iban}; ${booked.length} booked ${bookingDates[0]}..${bookingDates.at(-1)}; ${BUSINESS_INCOME_TRANSACTION_CODE} per month (${booked[0].currency}): ${describeMonthlyBusinessIncome(booked)}`;
}

async function checkHealth(settings: SmokeSettings): Promise<string> {
  const response = await requestJson(`${settings.gatewayUrl}/health`);
  assertStatus(response, HTTP_STATUS.OK, 'GET /health');
  assertEqual(readString(response.body, 'status'), 'ok', 'health status');
  return `${settings.gatewayUrl}/health status ok`;
}

async function checkUnknownConsent(settings: SmokeSettings): Promise<string> {
  const response = await requestJson(
    `${settings.gatewayUrl}/v1/consents/${randomUUID()}`,
  );
  return `GET /v1/consents/<random UUID> ${assertProblem(response, HTTP_STATUS.NOT_FOUND, 'CONSENT_UNKNOWN')}`;
}

async function checkConsentRevokedAtBank(
  settings: SmokeSettings,
  consentId: string,
): Promise<string> {
  const revocation = await requestJson(
    `${settings.sandboxApiBaseUrl}/v1/consents/${consentId}`,
    { method: 'DELETE', headers: { 'X-Request-ID': randomUUID() } },
  );
  assertStatus(revocation, HTTP_STATUS.NO_CONTENT, 'DELETE at the bank');
  const response = await requestJson(`${settings.gatewayUrl}/v1/accounts`, {
    headers: { 'Consent-ID': consentId },
  });
  return `bank DELETE 204, then GET /v1/accounts ${assertProblem(response, HTTP_STATUS.UNAUTHORIZED, 'CONSENT_INVALID')}`;
}

async function deleteConsentThroughGateway(
  settings: SmokeSettings,
  consentId: string,
): Promise<string> {
  const response = await requestJson(
    `${settings.gatewayUrl}/v1/consents/${consentId}`,
    { method: 'DELETE' },
  );
  assertStatus(
    response,
    HTTP_STATUS.NO_CONTENT,
    'DELETE /v1/consents/{consentId}',
  );
  return `DELETE 204, bank status ${await readConsentStatus(settings, consentId)}`;
}

function buildSteps(
  settings: SmokeSettings,
  createdConsents: CreatedConsent[],
): SmokeStep[] {
  const consentIdOf = (kind: ConsentKind): string =>
    findConsentId(createdConsents, kind);
  return [
    { name: 'health', run: () => checkHealth(settings) },
    {
      name: 'sandbox consent',
      run: () => authoriseConsent(settings, 'sandbox', createdConsents),
    },
    {
      name: 'sandbox data',
      run: () => checkSandboxData(settings, consentIdOf('sandbox')),
    },
    {
      name: 'persona consent',
      run: () => authoriseConsent(settings, 'persona', createdConsents),
    },
    {
      name: 'persona data',
      run: () => checkPersonaData(settings, consentIdOf('persona')),
    },
    { name: 'upstream 404', run: () => checkUnknownConsent(settings) },
    {
      name: 'upstream 401 sandbox consent',
      run: () => checkConsentRevokedAtBank(settings, consentIdOf('sandbox')),
    },
    {
      name: 'upstream 401 persona consent',
      run: () => checkConsentRevokedAtBank(settings, consentIdOf('persona')),
    },
  ];
}

function reportResult(
  outcome: StepOutcome,
  stepName: string,
  detail: string,
): void {
  process.stdout.write(`${outcome} ${stepName} - ${detail}\n`);
}

function describeError(error: unknown): string {
  if (!(error instanceof Error)) {
    return String(error);
  }
  const causeDescription = describeErrorCause(error.cause);
  return causeDescription === ''
    ? error.message
    : `${error.message} (${causeDescription})`;
}

// fetch reports network failures as "fetch failed" with the system error code on the cause.
function describeErrorCause(cause: unknown): string {
  if (isJsonRecord(cause) && typeof cause.code === 'string') {
    return cause.code;
  }
  return cause instanceof Error ? cause.message : '';
}

async function runStep(step: SmokeStep): Promise<boolean> {
  try {
    reportResult('PASS', step.name, await step.run());
    return true;
  } catch (error) {
    reportResult('FAIL', step.name, describeError(error));
    return false;
  }
}

async function runStepsUntilFirstFailure(
  steps: readonly SmokeStep[],
): Promise<boolean> {
  for (const step of steps) {
    if (!(await runStep(step))) {
      return false;
    }
  }
  return true;
}

async function deleteCreatedConsents(
  settings: SmokeSettings,
  createdConsents: readonly CreatedConsent[],
): Promise<boolean> {
  let isEveryConsentDeleted = true;
  for (const { kind, consentId } of createdConsents) {
    const isDeleted = await runStep({
      name: `cleanup ${kind} consent ${consentId}`,
      run: () => deleteConsentThroughGateway(settings, consentId),
    });
    isEveryConsentDeleted &&= isDeleted;
  }
  return isEveryConsentDeleted;
}

async function runSmoke(settings: SmokeSettings): Promise<boolean> {
  const createdConsents: CreatedConsent[] = [];
  let haveAllChecksPassed = false;
  try {
    haveAllChecksPassed = await runStepsUntilFirstFailure(
      buildSteps(settings, createdConsents),
    );
  } finally {
    const isCleanedUp = await deleteCreatedConsents(settings, createdConsents);
    haveAllChecksPassed &&= isCleanedUp;
  }
  return haveAllChecksPassed;
}

try {
  if (!(await runSmoke(readSettings(process.env)))) {
    process.exitCode = 1;
  }
} catch (error) {
  reportResult('FAIL', 'smoke setup', describeError(error));
  process.exitCode = 1;
}
