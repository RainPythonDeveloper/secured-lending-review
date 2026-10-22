import { resolve } from 'node:path';
import {
  InvalidGatewayConfigError,
  loadGatewayConfig,
} from './load-gateway-config.js';

const REQUIRED_VARIABLES = {
  TBC_API_BASE_URL: 'https://tbc-bank-mock-open-banking-api.vercel.app/0.8',
  TBC_OAUTH_AUTHORIZE_URL:
    'https://tbc-bank-mock-open-banking-api.vercel.app/psd2/openbanking/oauth/authorize',
  TBC_OAUTH_TOKEN_URL:
    'https://tbc-bank-mock-open-banking-api.vercel.app/openbanking/oauth/token',
  TBC_OAUTH_CLIENT_ID: 'virtual-field-visit-gateway',
  TBC_OAUTH_REDIRECT_URI: 'http://localhost:3000/oauth/callback',
  DATASET_XLSX_PATH: '../data/open-banking-synthetic-100-customers.xlsx',
};

function captureConfigError(env: NodeJS.ProcessEnv): InvalidGatewayConfigError {
  try {
    loadGatewayConfig(env);
  } catch (error) {
    if (error instanceof InvalidGatewayConfigError) {
      return error;
    }
    throw error;
  }
  throw new Error('Expected the environment to be rejected');
}

describe('loadGatewayConfig', () => {
  it('builds a typed config with defaults from the required variables', () => {
    const config = loadGatewayConfig({ ...REQUIRED_VARIABLES });

    expect(config).toEqual({
      port: 3000,
      tbc: {
        apiBaseUrl: REQUIRED_VARIABLES.TBC_API_BASE_URL,
        oauthAuthorizeUrl: REQUIRED_VARIABLES.TBC_OAUTH_AUTHORIZE_URL,
        oauthTokenUrl: REQUIRED_VARIABLES.TBC_OAUTH_TOKEN_URL,
        oauthClientId: REQUIRED_VARIABLES.TBC_OAUTH_CLIENT_ID,
        oauthRedirectUri: REQUIRED_VARIABLES.TBC_OAUTH_REDIRECT_URI,
        oauthUiLocale: 'en',
        httpTimeoutMs: 8000,
        retryMaxAttempts: 3,
        retryBaseDelayMs: 250,
        retryMaxDelayMs: 2000,
      },
      oauth: { stateTtlMs: 600000, tokenRefreshMarginMs: 60000 },
      dataset: {
        xlsxPath: resolve(process.cwd(), REQUIRED_VARIABLES.DATASET_XLSX_PATH),
      },
    });
  });

  it('parses explicitly set numeric and locale variables', () => {
    const config = loadGatewayConfig({
      ...REQUIRED_VARIABLES,
      PORT: '8080',
      TBC_OAUTH_UI_LOCALE: 'ka',
      TBC_HTTP_TIMEOUT_MS: '5000',
      TBC_RETRY_MAX_ATTEMPTS: '1',
      TBC_RETRY_BASE_DELAY_MS: '100',
      TBC_RETRY_MAX_DELAY_MS: '400',
      OAUTH_STATE_TTL_MS: '120000',
      OAUTH_TOKEN_REFRESH_MARGIN_MS: '0',
    });

    expect(config.port).toBe(8080);
    expect(config.tbc).toMatchObject({
      oauthUiLocale: 'ka',
      httpTimeoutMs: 5000,
      retryMaxAttempts: 1,
      retryBaseDelayMs: 100,
      retryMaxDelayMs: 400,
    });
    expect(config.oauth).toEqual({
      stateTtlMs: 120000,
      tokenRefreshMarginMs: 0,
    });
  });

  it('falls back to the default when an optional variable is empty', () => {
    const config = loadGatewayConfig({ ...REQUIRED_VARIABLES, PORT: '' });

    expect(config.port).toBe(3000);
  });

  it('strips trailing slashes from the API base URL', () => {
    const config = loadGatewayConfig({
      ...REQUIRED_VARIABLES,
      TBC_API_BASE_URL:
        'https://tbc-bank-mock-open-banking-api.vercel.app/0.8/',
    });

    expect(config.tbc.apiBaseUrl).toBe(
      'https://tbc-bank-mock-open-banking-api.vercel.app/0.8',
    );
  });

  it('keeps an absolute dataset path unchanged', () => {
    const config = loadGatewayConfig({
      ...REQUIRED_VARIABLES,
      DATASET_XLSX_PATH: '/app/data/open-banking-synthetic-100-customers.xlsx',
    });

    expect(config.dataset.xlsxPath).toBe(
      '/app/data/open-banking-synthetic-100-customers.xlsx',
    );
  });

  it.each(Object.keys(REQUIRED_VARIABLES))(
    'reports %s as required when it is missing',
    (variableName) => {
      const env = { ...REQUIRED_VARIABLES, [variableName]: undefined };

      const error = captureConfigError(env);

      expect(error.issues).toEqual([
        { variableName, message: `${variableName} is required` },
      ]);
    },
  );

  it('lists every missing required variable in one error', () => {
    const error = captureConfigError({});

    expect(error.issues.map((issue) => issue.variableName)).toEqual(
      Object.keys(REQUIRED_VARIABLES),
    );
    expect(error.message).toContain('TBC_API_BASE_URL is required');
    expect(error.message).toContain('DATASET_XLSX_PATH is required');
  });

  it.each([
    'TBC_API_BASE_URL',
    'TBC_OAUTH_AUTHORIZE_URL',
    'TBC_OAUTH_TOKEN_URL',
    'TBC_OAUTH_REDIRECT_URI',
  ])('rejects %s when it is not an http(s) URL', (variableName) => {
    const env = { ...REQUIRED_VARIABLES, [variableName]: 'ftp://example' };

    const error = captureConfigError(env);

    expect(error.issues).toEqual([
      { variableName, message: `${variableName} must be a URL address` },
    ]);
  });

  it.each([
    ['TBC_RETRY_MAX_ATTEMPTS', '4'],
    ['TBC_RETRY_MAX_ATTEMPTS', '0'],
    ['PORT', '65536'],
    ['PORT', '80a'],
    ['TBC_HTTP_TIMEOUT_MS', '2.5'],
    ['OAUTH_STATE_TTL_MS', '1000'],
    ['TBC_OAUTH_UI_LOCALE', 'de'],
  ])('rejects %s=%s', (variableName, value) => {
    const env = { ...REQUIRED_VARIABLES, [variableName]: value };

    const error = captureConfigError(env);

    expect(error.issues.map((issue) => issue.variableName)).toEqual([
      variableName,
    ]);
  });

  it('rejects a maximum retry delay below the base delay', () => {
    const env = {
      ...REQUIRED_VARIABLES,
      TBC_RETRY_BASE_DELAY_MS: '500',
      TBC_RETRY_MAX_DELAY_MS: '400',
    };

    const error = captureConfigError(env);

    expect(error.issues).toEqual([
      {
        variableName: 'TBC_RETRY_MAX_DELAY_MS',
        message:
          'TBC_RETRY_MAX_DELAY_MS must be greater than or equal to TBC_RETRY_BASE_DELAY_MS',
      },
    ]);
  });

  it('reports every invalid variable together', () => {
    const env = {
      ...REQUIRED_VARIABLES,
      TBC_API_BASE_URL: 'not a url',
      TBC_RETRY_MAX_ATTEMPTS: '4',
    };

    const error = captureConfigError(env);

    expect(error.issues.map((issue) => issue.variableName)).toEqual([
      'TBC_API_BASE_URL',
      'TBC_RETRY_MAX_ATTEMPTS',
    ]);
  });
});
