import request from 'supertest';
import {
  ProblemDetailsException,
  createProblem,
} from '../src/common/problem-details/problem-details.js';
import { authoriseConsent } from './support/authorise-consent.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';
import {
  upstreamConsentDetails,
  upstreamProblem,
} from './support/upstream-responses.js';

const NEVER_AUTHORISED_CONSENT_ID = '7c6b5a4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d';
const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';

describe('AIS accounts', () => {
  let testApp: TestApp;

  beforeEach(async () => {
    testApp = await createTestApp();
  });

  afterEach(async () => {
    await testApp.app.close();
  });

  function readAccounts(path: string, headers: Record<string, string> = {}) {
    return request(testApp.app.getHttpServer()).get(path).set(headers);
  }

  async function authorisePersonaConsent(psuId: string): Promise<string> {
    testApp.fakeTbcClient.getConsent.mockResolvedValue(
      upstreamConsentDetails(),
    );
    return authoriseConsent(testApp.app, testApp.fakeTbcClient, { psuId });
  }

  describe('GET /v1/accounts for a sandbox consent', () => {
    it('lists the bank accounts with gateway links and the TBC sandbox as data source', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      const response = await readAccounts('/v1/accounts?withBalance=true', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body.accounts).toHaveLength(2);
      expect(response.body.accounts[0]).toMatchObject({
        resourceId: 'acc-gel-001',
        iban: 'GE11TB1000000000000010',
        balances: [
          {
            balanceType: 'interimBooked',
            balanceAmount: { amount: '3247.50' },
          },
          {
            balanceType: 'interimAvailable',
            balanceAmount: { amount: '3225.00' },
          },
        ],
        _links: {
          account: { href: '/v1/accounts/acc-gel-001' },
          balances: { href: '/v1/accounts/acc-gel-001/balances' },
          transactions: { href: '/v1/accounts/acc-gel-001/transactions' },
        },
      });
    });

    it('calls the bank with the stored Bearer token and never returns it', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      const response = await readAccounts('/v1/accounts?withBalance=true', {
        'Consent-ID': consentId,
      });

      expect(testApp.fakeTbcClient.listAccounts).toHaveBeenCalledWith(
        { consentId, accessToken: 'access_fixture-not-a-real-token' },
        true,
        expect.objectContaining({ gatewayRequestId: expect.any(String) }),
      );
      expect(response.text).not.toContain('access_fixture');
      expect(response.text).not.toContain('/0.8/');
    });

    it.each([
      ['a missing Consent-ID header', {}],
      ['a Consent-ID that is not a UUID', { 'Consent-ID': 'consent-1' }],
    ])(
      'rejects %s with 400 FORMAT_ERROR without calling the bank',
      async (_case, headers) => {
        const response = await readAccounts('/v1/accounts', headers);

        expect(response.status).toBe(400);
        expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
        expect(response.body).toMatchObject({
          code: 'FORMAT_ERROR',
          detail: 'Consent-ID header must be a UUID',
        });
        expect(testApp.fakeTbcClient.listAccounts).not.toHaveBeenCalled();
      },
    );

    it('rejects withBalance values other than true and false with 400 FORMAT_ERROR', async () => {
      const response = await readAccounts('/v1/accounts?withBalance=yes', {
        'Consent-ID': NEVER_AUTHORISED_CONSENT_ID,
      });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('FORMAT_ERROR');
    });

    it('answers 401 TOKEN_INVALID for a consent never authorised through the gateway', async () => {
      const response = await readAccounts('/v1/accounts', {
        'Consent-ID': NEVER_AUTHORISED_CONSENT_ID,
      });

      expect(response.status).toBe(401);
      expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
      expect(response.body).toMatchObject({
        code: 'TOKEN_INVALID',
        detail: 'Consent has not been authorised through this gateway',
      });
    });

    it.each([
      [
        'a bank 401 TOKEN_INVALID',
        upstreamProblem(401, 'problem.token-invalid.401.json'),
        401,
        'TOKEN_INVALID',
      ],
      [
        'a bank 401 CONSENT_INVALID',
        upstreamProblem(401, 'problem.consent-invalid.401.json'),
        401,
        'CONSENT_INVALID',
      ],
      [
        'an injected bank failure',
        upstreamProblem(502, 'problem.service-unavailable.502.json'),
        502,
        'SERVICE_UNAVAILABLE',
      ],
      [
        'a bank timeout',
        new ProblemDetailsException(
          createProblem({
            status: 504,
            code: 'UPSTREAM_TIMEOUT',
            detail:
              'TBC sandbox did not answer listAccounts within 8000 ms (after 3 attempts)',
          }),
        ),
        504,
        'UPSTREAM_TIMEOUT',
      ],
    ])(
      'renders %s as problem+json with its status and code',
      async (_case, upstreamFailure, expectedStatus, expectedCode) => {
        const consentId = await authoriseConsent(
          testApp.app,
          testApp.fakeTbcClient,
        );
        testApp.fakeTbcClient.listAccounts.mockRejectedValue(upstreamFailure);

        const response = await readAccounts('/v1/accounts', {
          'Consent-ID': consentId,
        });

        expect(response.status).toBe(expectedStatus);
        expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
        expect(response.body.code).toBe(expectedCode);
      },
    );
  });

  describe('GET /v1/accounts/:accountId for a sandbox consent', () => {
    it('reads the account at the bank and links it to gateway routes', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      const response = await readAccounts('/v1/accounts/acc-gel-001', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body.account).toMatchObject({
        resourceId: 'acc-gel-001',
        _links: { account: { href: '/v1/accounts/acc-gel-001' } },
      });
      expect(testApp.fakeTbcClient.readAccountDetails).toHaveBeenCalledWith(
        expect.objectContaining({ consentId }),
        'acc-gel-001',
        false,
        expect.anything(),
      );
    });

    it('rejects an account id with characters outside the resourceId pattern with 400 FORMAT_ERROR', async () => {
      const response = await readAccounts('/v1/accounts/acc_gel_001', {
        'Consent-ID': NEVER_AUTHORISED_CONSENT_ID,
      });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('FORMAT_ERROR');
    });
  });

  describe('persona consents', () => {
    it('lists the current account of persona CUS-024 from the organizer dataset', async () => {
      const consentId = await authorisePersonaConsent('CUS-024');

      const response = await readAccounts('/v1/accounts', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('organizer-dataset');
      expect(response.body).toEqual({
        accounts: [
          {
            resourceId: 'ACC-0024',
            iban: 'GE38XX0000000000000024',
            currency: 'GEL',
            name: 'Current account',
            ownerName: 'Levan Gelashvili',
            cashAccountType: 'CACC',
            status: 'enabled',
            usage: 'PRIV',
            _links: {
              account: { href: '/v1/accounts/ACC-0024' },
              balances: { href: '/v1/accounts/ACC-0024/balances' },
              transactions: { href: '/v1/accounts/ACC-0024/transactions' },
            },
          },
        ],
      });
      expect(testApp.fakeTbcClient.listAccounts).not.toHaveBeenCalled();
    });

    it('lists both current accounts of persona CUS-011 with string balances', async () => {
      const consentId = await authorisePersonaConsent('CUS-011');

      const response = await readAccounts('/v1/accounts?withBalance=true', {
        'Consent-ID': consentId,
      });

      expect(
        response.body.accounts.map(
          (account: { resourceId: string }) => account.resourceId,
        ),
      ).toEqual(['ACC-0011', 'ACC-0179']);
      expect(response.body.accounts[1]).toMatchObject({
        iban: 'GE24XX0000000000000179',
        currency: 'USD',
        balances: [
          {
            balanceType: 'interimBooked',
            balanceAmount: { currency: 'USD', amount: '387.77' },
          },
          { balanceType: 'interimAvailable' },
        ],
      });
    });

    it('reads the details of the persona current account', async () => {
      const consentId = await authorisePersonaConsent('CUS-024');

      const response = await readAccounts('/v1/accounts/ACC-0024', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('organizer-dataset');
      expect(response.body.account).toMatchObject({
        resourceId: 'ACC-0024',
        iban: 'GE38XX0000000000000024',
      });
    });

    it('answers 404 RESOURCE_UNKNOWN for the persona savings account', async () => {
      const consentId = await authorisePersonaConsent('CUS-024');

      const response = await readAccounts('/v1/accounts/ACC-0143', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(404);
      expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
      expect(response.body).toMatchObject({
        code: 'RESOURCE_UNKNOWN',
        detail: 'Account resourceId not found',
      });
    });

    it('answers 401 CONSENT_INVALID when the bank reports the consent as terminated', async () => {
      const consentId = await authorisePersonaConsent('CUS-024');
      testApp.fakeTbcClient.getConsent.mockResolvedValue(
        upstreamConsentDetails({ consentStatus: 'terminatedByTpp' }),
      );

      const response = await readAccounts('/v1/accounts', {
        'Consent-ID': consentId,
      });

      expect(response.status).toBe(401);
      expect(response.body).toMatchObject({
        code: 'CONSENT_INVALID',
        detail: 'Consent is terminatedByTpp',
      });
    });
  });
});
