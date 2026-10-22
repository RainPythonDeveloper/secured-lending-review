import { fileURLToPath } from 'node:url';
import {
  DEFAULT_OAUTH_STATE_TTL_MS,
  DEFAULT_OAUTH_TOKEN_REFRESH_MARGIN_MS,
  DEFAULT_PORT,
  DEFAULT_TBC_HTTP_TIMEOUT_MS,
  DEFAULT_TBC_OAUTH_UI_LOCALE,
  DEFAULT_TBC_RETRY_BASE_DELAY_MS,
  DEFAULT_TBC_RETRY_MAX_ATTEMPTS,
  DEFAULT_TBC_RETRY_MAX_DELAY_MS,
} from '../../src/config/environment-variables.js';
import type { GatewayConfig } from '../../src/config/gateway-config.js';

const SANDBOX_ORIGIN = 'https://tbc-bank-mock-open-banking-api.vercel.app';

export const testGatewayConfig: GatewayConfig = {
  port: DEFAULT_PORT,
  tbc: {
    apiBaseUrl: `${SANDBOX_ORIGIN}/0.8`,
    oauthAuthorizeUrl: `${SANDBOX_ORIGIN}/psd2/openbanking/oauth/authorize`,
    oauthTokenUrl: `${SANDBOX_ORIGIN}/openbanking/oauth/token`,
    oauthClientId: 'virtual-field-visit-gateway',
    oauthRedirectUri: 'http://localhost:3000/oauth/callback',
    oauthUiLocale: DEFAULT_TBC_OAUTH_UI_LOCALE,
    httpTimeoutMs: DEFAULT_TBC_HTTP_TIMEOUT_MS,
    retryMaxAttempts: DEFAULT_TBC_RETRY_MAX_ATTEMPTS,
    retryBaseDelayMs: DEFAULT_TBC_RETRY_BASE_DELAY_MS,
    retryMaxDelayMs: DEFAULT_TBC_RETRY_MAX_DELAY_MS,
  },
  oauth: {
    stateTtlMs: DEFAULT_OAUTH_STATE_TTL_MS,
    tokenRefreshMarginMs: DEFAULT_OAUTH_TOKEN_REFRESH_MARGIN_MS,
  },
  dataset: {
    xlsxPath: fileURLToPath(
      new URL(
        '../../../data/open-banking-synthetic-100-customers.xlsx',
        import.meta.url,
      ),
    ),
  },
};
