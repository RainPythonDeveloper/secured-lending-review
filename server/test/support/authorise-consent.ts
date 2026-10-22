import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { computeCodeChallenge } from '../../src/oauth/pkce.js';
import { loadSandboxFixture } from '../fixtures/load-fixture.js';
import type { FakeTbcClient } from './fake-tbc-client.js';

export const AUTHORISATION_CODE = 'code_fixture-not-a-real-code';

export const bankOfferedConsentRequest = {
  access: { accounts: [], balances: [], transactions: [] },
  recurringIndicator: true,
  validUntil: '2026-11-21',
  frequencyPerDay: 4,
  combinedServiceIndicator: false,
};

export interface AuthoriseConsentOptions {
  readonly psuId?: string;
}

// Plays the PSU: creates a consent, "approves" it at the fake bank and follows the redirect to the callback.
export async function authoriseConsent(
  app: INestApplication,
  fakeTbcClient: FakeTbcClient,
  options: AuthoriseConsentOptions = {},
): Promise<string> {
  const psuHeaders: Record<string, string> =
    options.psuId === undefined ? {} : { 'PSU-ID': options.psuId };
  const created = await request(app.getHttpServer())
    .post('/v1/consents')
    .set(psuHeaders)
    .send(bankOfferedConsentRequest)
    .expect(201);
  const consentId: string = created.body.consentId;
  const scaRedirect = new URL(created.body._links.scaRedirect.href);
  expectTokenExchangeWithPkce(
    fakeTbcClient,
    consentId,
    scaRedirect.searchParams.get('code_challenge'),
  );
  await request(app.getHttpServer())
    .get('/oauth/callback')
    .query({
      state: scaRedirect.searchParams.get('state'),
      code: AUTHORISATION_CODE,
    })
    .expect(200);
  return consentId;
}

function expectTokenExchangeWithPkce(
  fakeTbcClient: FakeTbcClient,
  consentId: string,
  codeChallenge: string | null,
): void {
  const tokenFixture = loadSandboxFixture('token.200.json') as object;
  fakeTbcClient.exchangeAuthorisationCode.mockImplementationOnce(
    ({ codeVerifier }) =>
      computeCodeChallenge(codeVerifier) === codeChallenge
        ? Promise.resolve({ ...tokenFixture, scope: `AIS:${consentId}` })
        : Promise.reject(
            new Error('PKCE code verifier does not match the challenge'),
          ),
  );
}
