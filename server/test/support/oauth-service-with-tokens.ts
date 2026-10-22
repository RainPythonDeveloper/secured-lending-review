import { ConsentTokenStore } from '../../src/oauth/consent-token.store.js';
import { OAuthService } from '../../src/oauth/oauth.service.js';
import { PendingAuthorisationStore } from '../../src/oauth/pending-authorisation.store.js';
import type { TbcClientService } from '../../src/tbc-client/tbc-client.service.js';
import type { FakeTbcClient } from './fake-tbc-client.js';
import { FakeClock } from './fake-runtime.js';
import { testGatewayConfig } from './test-gateway-config.js';

export const STORED_ACCESS_TOKEN = 'access_fixture-not-a-real-token';

const NOW_MS = 1_792_670_000_000;
const ACCESS_TOKEN_LIFETIME_MS = 3_600_000;
const STORED_REFRESH_TOKEN = 'refresh_fixture-not-a-real-token';

// A real OAuthService whose store already holds fresh tokens for the given consents, as after /oauth/callback.
export function createOAuthServiceWithTokens(
  fakeTbcClient: FakeTbcClient,
  authorisedConsentIds: readonly string[],
): OAuthService {
  const clock = new FakeClock(NOW_MS);
  const consentTokens = new ConsentTokenStore();
  for (const consentId of authorisedConsentIds) {
    consentTokens.save(consentId, {
      accessToken: STORED_ACCESS_TOKEN,
      refreshToken: STORED_REFRESH_TOKEN,
      accessTokenExpiresAtMs: NOW_MS + ACCESS_TOKEN_LIFETIME_MS,
    });
  }
  return new OAuthService(
    fakeTbcClient as unknown as TbcClientService,
    new PendingAuthorisationStore(clock, testGatewayConfig),
    consentTokens,
    clock,
    testGatewayConfig,
  );
}
