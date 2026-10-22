import { isUUID } from 'class-validator';
import { loadSandboxFixture } from '../../test/fixtures/load-fixture.js';
import {
  createFakeTbcClient,
  type FakeTbcClient,
} from '../../test/support/fake-tbc-client.js';
import { FakeClock } from '../../test/support/fake-runtime.js';
import { testGatewayConfig } from '../../test/support/test-gateway-config.js';
import {
  ProblemDetailsException,
  createProblem,
} from '../common/problem-details/problem-details.js';
import type { TbcClientService } from '../tbc-client/tbc-client.service.js';
import type { UpstreamCallContext } from '../tbc-client/upstream-call-context.js';
import { ConsentTokenStore } from './consent-token.store.js';
import { OAuthService } from './oauth.service.js';
import { PendingAuthorisationStore } from './pending-authorisation.store.js';
import { computeCodeChallenge } from './pkce.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const UNKNOWN_STATE = '5b4a3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d';
const AUTHORISATION_CODE = 'code_fixture-not-a-real-code';
const START_MS = 1_792_670_000_000;
const ACCESS_TOKEN_LIFETIME_MS = 3_600_000;
const REFRESH_TOKEN_LIFETIME_MS = 7_776_000_000;
const REFRESH_MARGIN_MS = testGatewayConfig.oauth.tokenRefreshMarginMs;
const STATE_TTL_MS = testGatewayConfig.oauth.stateTtlMs;
const context: UpstreamCallContext = {
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
  psuIpAddress: '203.0.113.7',
};

function readAuthorisationParameter(
  authorisationUrl: string,
  parameterName: string,
): string {
  return new URL(authorisationUrl).searchParams.get(parameterName) ?? '';
}

function upstreamProblem(status: number, code: string, detail: string) {
  return new ProblemDetailsException(createProblem({ status, code, detail }));
}

describe('OAuthService', () => {
  let fakeTbcClient: FakeTbcClient;
  let clock: FakeClock;
  let consentTokens: ConsentTokenStore;
  let pendingAuthorisations: PendingAuthorisationStore;
  let oauthService: OAuthService;

  beforeEach(() => {
    fakeTbcClient = createFakeTbcClient();
    clock = new FakeClock(START_MS);
    consentTokens = new ConsentTokenStore();
    pendingAuthorisations = new PendingAuthorisationStore(
      clock,
      testGatewayConfig,
    );
    oauthService = new OAuthService(
      fakeTbcClient as unknown as TbcClientService,
      pendingAuthorisations,
      consentTokens,
      clock,
      testGatewayConfig,
    );
  });

  function startAuthorisationState(): string {
    const authorisationUrl = oauthService.startAuthorisation(CONSENT_ID);
    return readAuthorisationParameter(authorisationUrl, 'state');
  }

  async function authoriseConsent(): Promise<void> {
    await oauthService.completeAuthorisation(
      { state: startAuthorisationState(), code: AUTHORISATION_CODE },
      context,
    );
  }

  describe('startAuthorisation', () => {
    it('builds the bank authorisation URL with the consent scope and PKCE parameters', () => {
      const authorisationUrl = new URL(
        oauthService.startAuthorisation(CONSENT_ID),
      );

      expect(`${authorisationUrl.origin}${authorisationUrl.pathname}`).toBe(
        testGatewayConfig.tbc.oauthAuthorizeUrl,
      );
      expect(Object.fromEntries(authorisationUrl.searchParams)).toEqual({
        client_id: 'virtual-field-visit-gateway',
        scope: `AIS:${CONSENT_ID}`,
        response_type: 'code',
        redirect_uri: 'http://localhost:3000/oauth/callback',
        nonce: expect.any(String),
        state: expect.any(String),
        code_challenge_method: 'S256',
        code_challenge: expect.stringMatching(/^[A-Za-z0-9_-]{43}$/),
        ui_locales: 'en',
      });
    });

    it.each(['state', 'nonce'])('uses a random UUID as the %s', (name) => {
      const authorisationUrl = oauthService.startAuthorisation(CONSENT_ID);

      expect(
        isUUID(readAuthorisationParameter(authorisationUrl, name), 4),
      ).toBe(true);
    });

    it('remembers the code verifier that matches the code challenge', () => {
      const authorisationUrl = oauthService.startAuthorisation(CONSENT_ID);

      const pending = pendingAuthorisations.take(
        readAuthorisationParameter(authorisationUrl, 'state'),
      );

      expect(pending?.consentId).toBe(CONSENT_ID);
      expect(computeCodeChallenge(pending?.codeVerifier ?? '')).toBe(
        readAuthorisationParameter(authorisationUrl, 'code_challenge'),
      );
    });
  });

  describe('completeAuthorisation', () => {
    it('exchanges the code together with the code verifier of the state', async () => {
      const authorisationUrl = oauthService.startAuthorisation(CONSENT_ID);
      const state = readAuthorisationParameter(authorisationUrl, 'state');

      await oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      const [grant, grantContext] =
        fakeTbcClient.exchangeAuthorisationCode.mock.calls[0] ?? [];
      expect(grant?.code).toBe(AUTHORISATION_CODE);
      expect(computeCodeChallenge(grant?.codeVerifier ?? '')).toBe(
        readAuthorisationParameter(authorisationUrl, 'code_challenge'),
      );
      expect(grantContext).toBe(context);
    });

    it('returns the authorised consent and stores its tokens with expiry times', async () => {
      const state = startAuthorisationState();

      const authorisedConsent = await oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      expect(authorisedConsent).toEqual({ consentId: CONSENT_ID });
      expect(consentTokens.find(CONSENT_ID)).toEqual({
        accessToken: 'access_fixture-not-a-real-token',
        refreshToken: 'refresh_fixture-not-a-real-token',
        accessTokenExpiresAtMs: START_MS + ACCESS_TOKEN_LIFETIME_MS,
        refreshTokenExpiresAtMs: START_MS + REFRESH_TOKEN_LIFETIME_MS,
      });
    });

    it('rejects an unknown state with 400 STATE_INVALID', async () => {
      const completing = oauthService.completeAuthorisation(
        { state: UNKNOWN_STATE, code: AUTHORISATION_CODE },
        context,
      );

      await expect(completing).rejects.toMatchObject({
        problem: { status: 400, code: 'STATE_INVALID' },
      });
    });

    it('rejects a state that was already used with 400 STATE_INVALID', async () => {
      const state = startAuthorisationState();
      await oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      const completingAgain = oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      await expect(completingAgain).rejects.toMatchObject({
        problem: { status: 400, code: 'STATE_INVALID' },
      });
    });

    it('rejects an expired state with 400 STATE_INVALID', async () => {
      const state = startAuthorisationState();
      clock.advanceBy(STATE_TTL_MS + 1);

      const completing = oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      await expect(completing).rejects.toMatchObject({
        problem: { status: 400, code: 'STATE_INVALID' },
      });
    });

    it('reports a PSU who rejected the consent as 403 ACCESS_DENIED', async () => {
      const state = startAuthorisationState();

      const completing = oauthService.completeAuthorisation(
        { state, error: 'access_denied' },
        context,
      );

      await expect(completing).rejects.toMatchObject({
        problem: { status: 403, code: 'ACCESS_DENIED' },
      });
      expect(fakeTbcClient.exchangeAuthorisationCode).not.toHaveBeenCalled();
    });

    it('reports any other OAuth error as 400 with the uppercased error code', async () => {
      const state = startAuthorisationState();

      const completing = oauthService.completeAuthorisation(
        {
          state,
          error: 'invalid_scope',
          error_description: 'Consent in scope is unknown',
        },
        context,
      );

      await expect(completing).rejects.toMatchObject({
        problem: {
          status: 400,
          code: 'INVALID_SCOPE',
          detail: 'Consent in scope is unknown',
        },
      });
    });

    it('rejects a callback without code or error with 400 FORMAT_ERROR', async () => {
      const state = startAuthorisationState();

      const completing = oauthService.completeAuthorisation({ state }, context);

      await expect(completing).rejects.toMatchObject({
        problem: { status: 400, code: 'FORMAT_ERROR' },
      });
    });

    it('passes the bank rejection of the code through and stores nothing', async () => {
      const invalidGrant = upstreamProblem(
        400,
        'INVALID_GRANT',
        'Authorization code is expired, unknown, or already used',
      );
      fakeTbcClient.exchangeAuthorisationCode.mockRejectedValue(invalidGrant);
      const state = startAuthorisationState();

      const completing = oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      await expect(completing).rejects.toBe(invalidGrant);
      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(false);
    });

    it('rejects tokens issued for another consent with 502 and stores nothing', async () => {
      const tokenForOtherConsent = {
        ...(loadSandboxFixture('token.200.json') as Record<string, unknown>),
        scope: 'AIS:9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b',
      };
      fakeTbcClient.exchangeAuthorisationCode.mockResolvedValue(
        tokenForOtherConsent,
      );
      const state = startAuthorisationState();

      const completing = oauthService.completeAuthorisation(
        { state, code: AUTHORISATION_CODE },
        context,
      );

      await expect(completing).rejects.toMatchObject({
        problem: { status: 502, code: 'UPSTREAM_CONTRACT_VIOLATION' },
      });
      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(false);
    });
  });

  describe('getAccessToken', () => {
    it('rejects a consent that was never authorised with 401 TOKEN_INVALID', async () => {
      const reading = oauthService.getAccessToken(CONSENT_ID, context);

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 401,
          code: 'TOKEN_INVALID',
          detail: 'Consent has not been authorised through this gateway',
        },
      });
    });

    it('returns the stored access token without refreshing before the refresh margin', async () => {
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS - REFRESH_MARGIN_MS - 1);

      const accessToken = await oauthService.getAccessToken(
        CONSENT_ID,
        context,
      );

      expect(accessToken).toBe('access_fixture-not-a-real-token');
      expect(fakeTbcClient.refreshAccessToken).not.toHaveBeenCalled();
    });

    it('refreshes the access token once the refresh margin is reached', async () => {
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS - REFRESH_MARGIN_MS);

      const accessToken = await oauthService.getAccessToken(
        CONSENT_ID,
        context,
      );

      expect(accessToken).toBe('access_fixture-refreshed-not-a-real-token');
      expect(fakeTbcClient.refreshAccessToken).toHaveBeenCalledWith(
        'refresh_fixture-not-a-real-token',
        context,
      );
    });

    it('stores the rotated refresh token and the new expiry time', async () => {
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS);

      await oauthService.getAccessToken(CONSENT_ID, context);

      expect(consentTokens.find(CONSENT_ID)).toMatchObject({
        refreshToken: 'refresh_fixture-rotated-not-a-real-token',
        accessTokenExpiresAtMs: clock.nowMs() + ACCESS_TOKEN_LIFETIME_MS,
      });
    });

    it('refreshes only once for concurrent callers', async () => {
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS);

      const accessTokens = await Promise.all([
        oauthService.getAccessToken(CONSENT_ID, context),
        oauthService.getAccessToken(CONSENT_ID, context),
      ]);

      expect(accessTokens).toEqual([
        'access_fixture-refreshed-not-a-real-token',
        'access_fixture-refreshed-not-a-real-token',
      ]);
      expect(fakeTbcClient.refreshAccessToken).toHaveBeenCalledTimes(1);
    });

    it('forgets the tokens and answers 401 TOKEN_INVALID when the bank rejects the refresh', async () => {
      fakeTbcClient.refreshAccessToken.mockRejectedValue(
        upstreamProblem(
          400,
          'INVALID_GRANT',
          'Refresh token is expired or invalid',
        ),
      );
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS);

      const reading = oauthService.getAccessToken(CONSENT_ID, context);

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 401,
          code: 'TOKEN_INVALID',
          detail: 'Refresh token is expired or invalid',
        },
      });
      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(false);
    });

    it('keeps the tokens when the refresh fails because the bank is unavailable', async () => {
      const unavailable = upstreamProblem(
        502,
        'SERVICE_UNAVAILABLE',
        'Injected synthetic failure (after 1 attempt)',
      );
      fakeTbcClient.refreshAccessToken.mockRejectedValue(unavailable);
      await authoriseConsent();
      clock.advanceBy(ACCESS_TOKEN_LIFETIME_MS);

      const reading = oauthService.getAccessToken(CONSENT_ID, context);

      await expect(reading).rejects.toBe(unavailable);
      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(true);
    });
  });

  describe('forgetConsent', () => {
    it('forgets the tokens and the pending states of the consent', async () => {
      await authoriseConsent();
      oauthService.startAuthorisation(CONSENT_ID);

      oauthService.forgetConsent(CONSENT_ID);

      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(false);
      expect(pendingAuthorisations.size).toBe(0);
    });
  });
});
