import request from 'supertest';
import { loadSandboxFixture } from './fixtures/load-fixture.js';
import { authoriseConsent } from './support/authorise-consent.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';
import { upstreamConsentDetails } from './support/upstream-responses.js';

const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';
const PERSONA_COVERAGE_END_DATE = '2026-05-08';

describe('AIS balances', () => {
  let testApp: TestApp;

  beforeEach(async () => {
    testApp = await createTestApp();
  });

  afterEach(async () => {
    await testApp.app.close();
  });

  function readBalances(accountId: string, consentId: string) {
    return request(testApp.app.getHttpServer())
      .get(`/v1/accounts/${accountId}/balances`)
      .set({ 'Consent-ID': consentId });
  }

  async function authorisePersonaConsent(): Promise<string> {
    testApp.fakeTbcClient.getConsent.mockResolvedValue(
      upstreamConsentDetails(),
    );
    return authoriseConsent(testApp.app, testApp.fakeTbcClient, {
      psuId: 'CUS-024',
    });
  }

  it('answers the bank balances of a sandbox consent unchanged', async () => {
    const consentId = await authoriseConsent(
      testApp.app,
      testApp.fakeTbcClient,
    );

    const response = await readBalances('acc-gel-001', consentId);

    expect(response.status).toBe(200);
    expect(response.headers['x-data-source']).toBe('tbc-sandbox');
    expect(response.body).toEqual(
      loadSandboxFixture('balances.acc-gel-001.200.json'),
    );
    expect(testApp.fakeTbcClient.readBalances).toHaveBeenCalledWith(
      { consentId, accessToken: 'access_fixture-not-a-real-token' },
      'acc-gel-001',
      expect.objectContaining({ gatewayRequestId: expect.any(String) }),
    );
  });

  it('answers the closing balance of a persona account as string amounts', async () => {
    const consentId = await authorisePersonaConsent();

    const response = await readBalances('ACC-0024', consentId);

    expect(response.status).toBe(200);
    expect(response.headers['x-data-source']).toBe('organizer-dataset');
    expect(response.body).toEqual({
      account: { iban: 'GE38XX0000000000000024', currency: 'GEL' },
      balances: [
        {
          balanceType: 'interimBooked',
          balanceAmount: { currency: 'GEL', amount: '1819.62' },
          creditLimitIncluded: false,
          referenceDate: PERSONA_COVERAGE_END_DATE,
        },
        {
          balanceType: 'interimAvailable',
          balanceAmount: { currency: 'GEL', amount: '1819.62' },
          creditLimitIncluded: false,
          referenceDate: PERSONA_COVERAGE_END_DATE,
        },
      ],
    });
  });

  it('answers 403 CONSENT_INVALID for a persona consent to the account list only', async () => {
    const consentId = await authorisePersonaConsent();
    testApp.fakeTbcClient.getConsent.mockResolvedValue(
      upstreamConsentDetails({ access: { availableAccounts: 'allAccounts' } }),
    );

    const response = await readBalances('ACC-0024', consentId);

    expect(response.status).toBe(403);
    expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
    expect(response.body).toMatchObject({
      code: 'CONSENT_INVALID',
      detail: 'Consent does not allow balances for this account',
    });
  });
});
