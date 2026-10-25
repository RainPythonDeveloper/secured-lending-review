import { Logger } from '@nestjs/common';
import { isUUID } from 'class-validator';
import type { Mock, MockInstance } from 'vitest';
import {
  loadSandboxFixture,
  readSandboxFixtureText,
} from '../../test/fixtures/load-fixture.js';
import {
  FakeClock,
  FixedRandomSource,
  RecordingSleeper,
} from '../../test/support/fake-runtime.js';
import { testGatewayConfig } from '../../test/support/test-gateway-config.js';
import {
  ProblemDetailsException,
  createProblem,
} from '../common/problem-details/problem-details.js';
import type { FetchFunction } from './fetch.token.js';
import { RetryPolicy } from './retry-policy.js';
import { TbcHttpTransport, type TbcHttpRequest } from './tbc-http-transport.js';

const GATEWAY_REQUEST_ID = '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c';
const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const ACCESS_TOKEN = 'access_fixture-not-a-real-token';
const ATTEMPT_DURATION_MS = 120;
const API_BASE_URL = testGatewayConfig.tbc.apiBaseUrl;

const readTransactionsRequest: TbcHttpRequest = {
  operationName: 'readTransactions',
  method: 'GET',
  url: `${API_BASE_URL}/v1/accounts/acc-gel-001/transactions?bookingStatus=both`,
  headers: {
    'Consent-ID': CONSENT_ID,
    Authorization: `Bearer ${ACCESS_TOKEN}`,
  },
  context: { gatewayRequestId: GATEWAY_REQUEST_ID },
};

const createConsentRequest: TbcHttpRequest = {
  operationName: 'createConsent',
  method: 'POST',
  url: `${API_BASE_URL}/v1/consents`,
  headers: { 'Content-Type': 'application/json' },
  body: '{"recurringIndicator":true}',
  context: { gatewayRequestId: GATEWAY_REQUEST_ID },
};

const deleteConsentRequest: TbcHttpRequest = {
  operationName: 'deleteConsent',
  method: 'DELETE',
  url: `${API_BASE_URL}/v1/consents/${CONSENT_ID}`,
  headers: {},
  context: { gatewayRequestId: GATEWAY_REQUEST_ID },
};

function fixtureResponse(fileName: string, status: number): Response {
  return new Response(readSandboxFixtureText(fileName), { status });
}

function injectedFailure(status = 502): Response {
  return fixtureResponse('problem.service-unavailable.502.json', status);
}

function sentRequestIds(fetchMock: Mock<FetchFunction>): (string | null)[] {
  return fetchMock.mock.calls.map(([, init]) =>
    new Headers(init?.headers).get('X-Request-ID'),
  );
}

describe('TbcHttpTransport', () => {
  let fetchMock: Mock<FetchFunction>;
  let sleeper: RecordingSleeper;
  let transport: TbcHttpTransport;
  let logSpy: MockInstance<Logger['log']>;
  let warnSpy: MockInstance<Logger['warn']>;

  beforeEach(() => {
    const clock = new FakeClock(0);
    fetchMock = vi.fn<FetchFunction>();
    sleeper = new RecordingSleeper();
    transport = new TbcHttpTransport(
      async (input, init) => {
        clock.advanceBy(ATTEMPT_DURATION_MS);
        return fetchMock(input, init);
      },
      testGatewayConfig,
      new RetryPolicy(testGatewayConfig, new FixedRandomSource(0.5)),
      sleeper,
      clock,
    );
    logSpy = vi
      .spyOn(Logger.prototype, 'log')
      .mockImplementation(() => undefined);
    warnSpy = vi
      .spyOn(Logger.prototype, 'warn')
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('retries GET transactions after injected 502', async () => {
    fetchMock
      .mockResolvedValueOnce(injectedFailure())
      .mockResolvedValueOnce(
        fixtureResponse('transactions.acc-gel-001.both.200.json', 200),
      );

    const body = await transport.send(readTransactionsRequest);

    expect(body).toEqual(
      loadSandboxFixture('transactions.acc-gel-001.both.200.json'),
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(sleeper.sleptDurationsMs).toEqual([187.5]);
  });

  it('gives up after 3 attempts and returns 502 with the upstream code', async () => {
    fetchMock.mockImplementation(async () => injectedFailure(503));

    const sending = transport.send(readTransactionsRequest);

    await expect(sending).rejects.toMatchObject({
      problem: createProblem({
        status: 502,
        code: 'SERVICE_UNAVAILABLE',
        detail: 'Injected synthetic failure (after 3 attempts)',
      }),
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(sleeper.sleptDurationsMs).toEqual([187.5, 375]);
  });

  it('does not retry POST consent creation after 502', async () => {
    fetchMock.mockResolvedValueOnce(injectedFailure());

    const sending = transport.send(createConsentRequest);

    await expect(sending).rejects.toMatchObject({
      problem: {
        status: 502,
        code: 'SERVICE_UNAVAILABLE',
        detail: 'Injected synthetic failure (after 1 attempt)',
      },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(sleeper.sleptDurationsMs).toEqual([]);
  });

  it('does not retry GET after 404 and keeps status and code', async () => {
    fetchMock.mockResolvedValueOnce(
      fixtureResponse('problem.consent-unknown.404.json', 404),
    );

    const sending = transport.send(readTransactionsRequest);

    await expect(sending).rejects.toMatchObject({
      problem: loadSandboxFixture('problem.consent-unknown.404.json'),
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('passes an OAuth error through as problem details', async () => {
    fetchMock.mockResolvedValueOnce(
      fixtureResponse('token.invalid-grant.400.json', 400),
    );

    const sending = transport.send(createConsentRequest);

    await expect(sending).rejects.toMatchObject({
      problem: {
        status: 400,
        code: 'INVALID_GRANT',
        detail: 'Authorization code is expired, unknown, or already used',
      },
    });
  });

  it('retries after a timeout and returns 504 UPSTREAM_TIMEOUT when exhausted', async () => {
    fetchMock.mockRejectedValue(
      new DOMException('The operation timed out.', 'TimeoutError'),
    );

    const sending = transport.send(readTransactionsRequest);

    await expect(sending).rejects.toMatchObject({
      problem: createProblem({
        status: 504,
        code: 'UPSTREAM_TIMEOUT',
        detail:
          'TBC sandbox did not answer readTransactions within 8000 ms (after 3 attempts)',
      }),
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('reports an unreachable sandbox as 502 SERVICE_UNAVAILABLE without retrying', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));

    const sending = transport.send(readTransactionsRequest);

    await expect(sending).rejects.toMatchObject({
      problem: {
        status: 502,
        code: 'SERVICE_UNAVAILABLE',
        detail: 'TBC sandbox could not be reached for readTransactions',
      },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('uses a new X-Request-ID on every attempt', async () => {
    fetchMock.mockImplementation(async () => injectedFailure());

    await expect(transport.send(readTransactionsRequest)).rejects.toThrow(
      ProblemDetailsException,
    );
    const requestIds = sentRequestIds(fetchMock);

    expect(requestIds).toHaveLength(3);
    expect(new Set(requestIds).size).toBe(3);
    expect(requestIds.every((requestId) => isUUID(requestId, 4))).toBe(true);
    expect(requestIds).not.toContain(GATEWAY_REQUEST_ID);
  });

  it('sends the request headers, Accept JSON and a timeout signal', async () => {
    fetchMock.mockResolvedValueOnce(
      fixtureResponse('create-consent.201.json', 201),
    );

    await transport.send(createConsentRequest);
    const [url, init] = fetchMock.mock.calls[0] ?? [];

    expect(url).toBe(`${API_BASE_URL}/v1/consents`);
    expect(init).toMatchObject({
      method: 'POST',
      body: '{"recurringIndicator":true}',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  });

  it('logs one line per attempt without Authorization or token values', async () => {
    fetchMock
      .mockResolvedValueOnce(injectedFailure())
      .mockResolvedValueOnce(
        fixtureResponse('transactions.acc-gel-001.both.200.json', 200),
      );

    await transport.send(readTransactionsRequest);
    const [upstreamRequestId1, upstreamRequestId2] = sentRequestIds(fetchMock);
    const loggedText = JSON.stringify([
      ...warnSpy.mock.calls,
      ...logSpy.mock.calls,
    ]);

    expect(warnSpy.mock.calls).toEqual([
      [
        `readTransactions attempt 1/3 upstreamRequestId=${upstreamRequestId1} gatewayRequestId=${GATEWAY_REQUEST_ID} status 502 in 120 ms, retrying in 188 ms`,
      ],
    ]);
    expect(logSpy.mock.calls).toEqual([
      [
        `readTransactions attempt 2/3 upstreamRequestId=${upstreamRequestId2} gatewayRequestId=${GATEWAY_REQUEST_ID} status 200 in 120 ms`,
      ],
    ]);
    expect(loggedText).not.toContain(ACCESS_TOKEN);
    expect(loggedText).not.toContain('Bearer');
    expect(loggedText).not.toContain(CONSENT_ID);
    expect(loggedText).not.toContain('bookingStatus');
  });

  it('returns undefined for 204', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    const body = await transport.send(deleteConsentRequest);

    expect(body).toBeUndefined();
  });

  it('rejects non-JSON 2xx as UPSTREAM_CONTRACT_VIOLATION', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('<html>ok</html>', { status: 200 }),
    );

    const sending = transport.send(readTransactionsRequest);

    await expect(sending).rejects.toMatchObject({
      problem: {
        status: 502,
        code: 'UPSTREAM_CONTRACT_VIOLATION',
        detail:
          'TBC sandbox answered readTransactions with a body that is not valid JSON',
      },
    });
  });
});
