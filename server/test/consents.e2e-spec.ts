import { isUUID } from 'class-validator';
import request from 'supertest';
import { ProblemDetailsException } from '../src/common/problem-details/problem-details.js';
import { parseUpstreamProblem } from '../src/tbc-client/upstream-problem.js';
import { readSandboxFixtureText } from './fixtures/load-fixture.js';
import {
  authoriseConsent,
  bankOfferedConsentRequest,
} from './support/authorise-consent.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';

const FIXTURE_CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';

function upstreamProblem(status: number, fixtureFileName: string) {
  return new ProblemDetailsException(
    parseUpstreamProblem(status, readSandboxFixtureText(fixtureFileName)),
  );
}

describe('AIS consents', () => {
  let testApp: TestApp;

  beforeEach(async () => {
    testApp = await createTestApp();
  });

  afterEach(async () => {
    await testApp.app.close();
  });

  function createConsent(headers: Record<string, string> = {}) {
    return request(testApp.app.getHttpServer())
      .post('/v1/consents')
      .set(headers)
      .send(bankOfferedConsentRequest);
  }

  describe('POST /v1/consents', () => {
    it('answers 201 with the consent, its gateway links and the TBC sandbox as data source', async () => {
      const response = await createConsent();

      expect(response.status).toBe(201);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body).toMatchObject({
        consentId: FIXTURE_CONSENT_ID,
        consentStatus: 'received',
        _links: {
          self: { href: `/v1/consents/${FIXTURE_CONSENT_ID}` },
          status: { href: `/v1/consents/${FIXTURE_CONSENT_ID}/status` },
        },
        psuMessage: expect.stringContaining('synthetic TBC mock sandbox'),
      });
    });

    it('links to the bank authorisation page with the consent scope and PKCE', async () => {
      const response = await createConsent();

      const scaRedirect = new URL(response.body._links.scaRedirect.href);
      expect(`${scaRedirect.origin}${scaRedirect.pathname}`).toBe(
        'https://tbc-bank-mock-open-banking-api.vercel.app/psd2/openbanking/oauth/authorize',
      );
      expect(Object.fromEntries(scaRedirect.searchParams)).toMatchObject({
        client_id: 'virtual-field-visit-gateway',
        scope: `AIS:${FIXTURE_CONSENT_ID}`,
        response_type: 'code',
        redirect_uri: 'http://localhost:3000/oauth/callback',
        code_challenge_method: 'S256',
      });
      expect(isUUID(scaRedirect.searchParams.get('state'), 4)).toBe(true);
    });

    it('forwards the consent request and PSU-ID to the bank', async () => {
      await createConsent({ 'PSU-ID': 'CUS-024' });

      expect(testApp.fakeTbcClient.createConsent).toHaveBeenCalledWith(
        bankOfferedConsentRequest,
        'CUS-024',
        expect.objectContaining({ gatewayRequestId: expect.any(String) }),
      );
    });

    it('serves a consent created for a dataset customer from the organizer dataset', async () => {
      const response = await createConsent({ 'PSU-ID': 'CUS-024' });

      expect(response.status).toBe(201);
      expect(response.headers['x-data-source']).toBe('organizer-dataset');
      expect(response.body.psuMessage).toContain(
        'organizer dataset persona CUS-024',
      );
    });

    it('falls back to the TBC sandbox for a PSU-ID that is not in the dataset', async () => {
      const response = await createConsent({ 'PSU-ID': 'CUS-999' });

      expect(response.status).toBe(201);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body.psuMessage).toContain(
        'not an organizer dataset customer',
      );
    });

    it('rejects a malformed PSU-ID with 400 FORMAT_ERROR', async () => {
      const response = await createConsent({ 'PSU-ID': 'CUS_024' });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('FORMAT_ERROR');
    });

    it.each([
      [
        'a capitalised Accounts key',
        { ...bankOfferedConsentRequest, access: { Accounts: [] } },
        'property Accounts should not exist',
      ],
      [
        'frequencyPerDay 9',
        { ...bankOfferedConsentRequest, frequencyPerDay: 9 },
        'frequencyPerDay must not be greater than 4',
      ],
      [
        'a validUntil that is not an ISO date',
        { ...bankOfferedConsentRequest, validUntil: '21.11.2026' },
        'validUntil must match',
      ],
      [
        'a numeric recurringIndicator',
        { ...bankOfferedConsentRequest, recurringIndicator: 1 },
        'recurringIndicator must be a boolean value',
      ],
    ])(
      'rejects a request with %s as 400 FORMAT_ERROR without calling the bank',
      async (_case, body, expectedMessage) => {
        const response = await request(testApp.app.getHttpServer())
          .post('/v1/consents')
          .send(body);

        expect(response.status).toBe(400);
        expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
        expect(response.body.code).toBe('FORMAT_ERROR');
        expect(response.body.detail).toContain(expectedMessage);
        expect(testApp.fakeTbcClient.createConsent).not.toHaveBeenCalled();
      },
    );

    it('passes a bank FORMAT_ERROR through as problem+json', async () => {
      testApp.fakeTbcClient.createConsent.mockRejectedValue(
        upstreamProblem(400, 'problem.format-error.400.json'),
      );

      const response = await createConsent();

      expect(response.status).toBe(400);
      expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
      expect(response.body).toMatchObject({
        code: 'FORMAT_ERROR',
        detail: 'body.recurringIndicator is required',
      });
    });
  });

  describe('authorisation', () => {
    it('stores tokens for the consent once the PSU returns through the OAuth callback with PKCE', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      expect(testApp.oauthService.hasAuthorisedTokens(consentId)).toBe(true);
    });
  });

  describe('GET /v1/consents/:consentId', () => {
    it('answers with the bank consent details without the upstream links', async () => {
      const response = await request(testApp.app.getHttpServer()).get(
        `/v1/consents/${FIXTURE_CONSENT_ID}`,
      );

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body).toMatchObject({
        consentStatus: 'valid',
        validUntil: '2026-11-21',
        frequencyPerDay: 4,
        access: {
          accounts: [
            { iban: 'GE11TB1000000000000010' },
            { iban: 'GE22TB2000000000000020' },
          ],
        },
      });
      expect(response.body).not.toHaveProperty('_links');
    });

    it('reports the organizer dataset as data source of a persona consent', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
        { psuId: 'CUS-024' },
      );

      const response = await request(testApp.app.getHttpServer()).get(
        `/v1/consents/${consentId}`,
      );

      expect(response.headers['x-data-source']).toBe('organizer-dataset');
    });

    it('renders a consent unknown to the bank as 404 CONSENT_UNKNOWN problem+json', async () => {
      testApp.fakeTbcClient.getConsent.mockRejectedValue(
        upstreamProblem(404, 'problem.consent-unknown.404.json'),
      );

      const response = await request(testApp.app.getHttpServer()).get(
        `/v1/consents/${FIXTURE_CONSENT_ID}`,
      );

      expect(response.status).toBe(404);
      expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
      expect(response.body.code).toBe('CONSENT_UNKNOWN');
    });

    it('rejects a consent id that is not a UUID with 400 FORMAT_ERROR', async () => {
      const response = await request(testApp.app.getHttpServer()).get(
        '/v1/consents/consent-1',
      );

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('FORMAT_ERROR');
      expect(testApp.fakeTbcClient.getConsent).not.toHaveBeenCalled();
    });
  });

  describe('GET /v1/consents/:consentId/status', () => {
    it('answers with the bank consent status', async () => {
      const response = await request(testApp.app.getHttpServer()).get(
        `/v1/consents/${FIXTURE_CONSENT_ID}/status`,
      );

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body).toEqual({ consentStatus: 'valid' });
    });
  });

  describe('DELETE /v1/consents/:consentId', () => {
    it('terminates the consent at the bank and answers 204 with its data source', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
        { psuId: 'CUS-024' },
      );

      const response = await request(testApp.app.getHttpServer()).delete(
        `/v1/consents/${consentId}`,
      );

      expect(response.status).toBe(204);
      expect(response.text).toBe('');
      expect(response.headers['x-data-source']).toBe('organizer-dataset');
      expect(testApp.fakeTbcClient.deleteConsent).toHaveBeenCalledWith(
        consentId,
        expect.objectContaining({ gatewayRequestId: expect.any(String) }),
      );
    });

    it('forgets the tokens and the persona binding of the deleted consent', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
        { psuId: 'CUS-024' },
      );

      await request(testApp.app.getHttpServer()).delete(
        `/v1/consents/${consentId}`,
      );
      const statusResponse = await request(testApp.app.getHttpServer()).get(
        `/v1/consents/${consentId}/status`,
      );

      expect(testApp.oauthService.hasAuthorisedTokens(consentId)).toBe(false);
      expect(statusResponse.headers['x-data-source']).toBe('tbc-sandbox');
    });
  });
});
