import type { Mock } from 'vitest';
import { testGatewayConfig } from '../../test/support/test-gateway-config.js';
import { TbcClientService } from './tbc-client.service.js';
import type { TbcHttpRequest, TbcHttpTransport } from './tbc-http-transport.js';
import type {
  UpstreamAuthorisation,
  UpstreamCallContext,
} from './upstream-call-context.js';

const API_BASE_URL = 'https://tbc-bank-mock-open-banking-api.vercel.app/0.8';
const TOKEN_URL =
  'https://tbc-bank-mock-open-banking-api.vercel.app/openbanking/oauth/token';
const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const context: UpstreamCallContext = {
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
  psuIpAddress: '203.0.113.7',
};
const authorisation: UpstreamAuthorisation = {
  consentId: CONSENT_ID,
  accessToken: 'access_fixture-not-a-real-token',
};
const accountReadHeaders = {
  'PSU-IP-Address': '203.0.113.7',
  'Consent-ID': CONSENT_ID,
  Authorization: 'Bearer access_fixture-not-a-real-token',
};

describe('TbcClientService', () => {
  let send: Mock<(request: TbcHttpRequest) => Promise<unknown>>;
  let client: TbcClientService;

  beforeEach(() => {
    send = vi.fn().mockResolvedValue({});
    client = new TbcClientService(
      { send } as unknown as TbcHttpTransport,
      testGatewayConfig,
    );
  });

  function sentRequest(): TbcHttpRequest | undefined {
    return send.mock.calls[0]?.[0];
  }

  it('creates a consent with the redirect headers, PSU headers and JSON body', async () => {
    await client.createConsent(
      { recurringIndicator: true },
      'CUS-024',
      context,
    );

    expect(sentRequest()).toEqual({
      operationName: 'createConsent',
      method: 'POST',
      url: `${API_BASE_URL}/v1/consents`,
      headers: {
        'PSU-IP-Address': '203.0.113.7',
        'PSU-ID': 'CUS-024',
        'Content-Type': 'application/json',
        'TPP-Redirect-URI': 'http://localhost:3000/oauth/callback',
        'TPP-Redirect-Preferred': 'true',
      },
      body: '{"recurringIndicator":true}',
      context,
    });
  });

  it('omits PSU-ID and PSU-IP-Address when they are unknown', async () => {
    await client.createConsent({}, undefined, { gatewayRequestId: 'id' });

    expect(sentRequest()?.headers).not.toHaveProperty('PSU-ID');
    expect(sentRequest()?.headers).not.toHaveProperty('PSU-IP-Address');
  });

  it.each([
    ['getConsent', 'GET', `${API_BASE_URL}/v1/consents/${CONSENT_ID}`],
    [
      'getConsentStatus',
      'GET',
      `${API_BASE_URL}/v1/consents/${CONSENT_ID}/status`,
    ],
    ['deleteConsent', 'DELETE', `${API_BASE_URL}/v1/consents/${CONSENT_ID}`],
  ] as const)('%s sends %s %s', async (methodName, httpMethod, url) => {
    await client[methodName](CONSENT_ID, context);

    expect(sentRequest()).toMatchObject({
      operationName: methodName,
      method: httpMethod,
      url,
      headers: { 'PSU-IP-Address': '203.0.113.7' },
    });
  });

  it('encodes path segments taken from the caller', async () => {
    await client.getConsent('a/../b c', context);

    expect(sentRequest()?.url).toBe(
      `${API_BASE_URL}/v1/consents/a%2F..%2Fb%20c`,
    );
  });

  it('exchanges an authorisation code with a form body for the public client', async () => {
    await client.exchangeAuthorisationCode(
      { code: 'code_fixture', codeVerifier: 'verifier_fixture' },
      context,
    );

    expect(sentRequest()).toMatchObject({
      operationName: 'exchangeAuthorisationCode',
      method: 'POST',
      url: TOKEN_URL,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    expect(
      Object.fromEntries(new URLSearchParams(sentRequest()?.body)),
    ).toEqual({
      client_id: 'virtual-field-visit-gateway',
      grant_type: 'authorization_code',
      code: 'code_fixture',
      code_verifier: 'verifier_fixture',
      redirect_uri: 'http://localhost:3000/oauth/callback',
    });
  });

  it('refreshes an access token with the refresh_token grant', async () => {
    await client.refreshAccessToken(
      'refresh_fixture-not-a-real-token',
      context,
    );

    expect(sentRequest()).toMatchObject({ method: 'POST', url: TOKEN_URL });
    expect(
      Object.fromEntries(new URLSearchParams(sentRequest()?.body)),
    ).toEqual({
      client_id: 'virtual-field-visit-gateway',
      grant_type: 'refresh_token',
      refresh_token: 'refresh_fixture-not-a-real-token',
    });
  });

  it('lists accounts with balances using Consent-ID and the Bearer token', async () => {
    await client.listAccounts(authorisation, true, context);

    expect(sentRequest()).toMatchObject({
      operationName: 'listAccounts',
      method: 'GET',
      url: `${API_BASE_URL}/v1/accounts?withBalance=true`,
      headers: accountReadHeaders,
    });
  });

  it('omits withBalance when balances are not requested', async () => {
    await client.readAccountDetails(
      authorisation,
      'acc-gel-001',
      false,
      context,
    );

    expect(sentRequest()).toMatchObject({
      operationName: 'readAccountDetails',
      url: `${API_BASE_URL}/v1/accounts/acc-gel-001`,
      headers: accountReadHeaders,
    });
  });

  it('reads balances of one account', async () => {
    await client.readBalances(authorisation, 'acc-gel-001', context);

    expect(sentRequest()).toMatchObject({
      operationName: 'readBalances',
      method: 'GET',
      url: `${API_BASE_URL}/v1/accounts/acc-gel-001/balances`,
      headers: accountReadHeaders,
    });
  });

  it('reads transactions with only the query parameters that are set', async () => {
    await client.readTransactions(
      authorisation,
      'acc-gel-001',
      { dateFrom: '2026-10-01', bookingStatus: 'both' },
      context,
    );

    expect(sentRequest()).toMatchObject({
      operationName: 'readTransactions',
      method: 'GET',
      url: `${API_BASE_URL}/v1/accounts/acc-gel-001/transactions?dateFrom=2026-10-01&bookingStatus=both`,
      headers: accountReadHeaders,
    });
  });

  it('returns the body produced by the transport', async () => {
    send.mockResolvedValueOnce({ consentStatus: 'valid' });

    const body = await client.getConsentStatus(CONSENT_ID, context);

    expect(body).toEqual({ consentStatus: 'valid' });
  });
});
