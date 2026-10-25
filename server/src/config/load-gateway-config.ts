import { resolve } from 'node:path';
import { plainToInstance } from 'class-transformer';
import { validateSync, type ValidationError } from 'class-validator';
import { EnvironmentVariables } from './environment-variables.js';
import type { GatewayConfig } from './gateway-config.js';

const TRAILING_SLASHES_PATTERN = /\/+$/;

export interface GatewayConfigIssue {
  readonly variableName: string;
  readonly message: string;
}

export class InvalidGatewayConfigError extends Error {
  constructor(readonly issues: readonly GatewayConfigIssue[]) {
    super(
      `Invalid gateway configuration: ${issues.map((issue) => issue.message).join('; ')}`,
    );
    this.name = 'InvalidGatewayConfigError';
  }
}

export function loadGatewayConfig(env: NodeJS.ProcessEnv): GatewayConfig {
  const variables = plainToInstance(EnvironmentVariables, env, {
    excludeExtraneousValues: true,
  });
  const issues = [
    ...validateSync(variables, { stopAtFirstError: true }).map(toConfigIssue),
    ...findRetryDelayIssues(variables),
  ];
  if (issues.length > 0) {
    throw new InvalidGatewayConfigError(issues);
  }
  return toGatewayConfig(variables);
}

function toConfigIssue(error: ValidationError): GatewayConfigIssue {
  return {
    variableName: error.property,
    message: Object.values(error.constraints ?? {}).join(', '),
  };
}

function findRetryDelayIssues(
  variables: EnvironmentVariables,
): GatewayConfigIssue[] {
  const { TBC_RETRY_BASE_DELAY_MS, TBC_RETRY_MAX_DELAY_MS } = variables;
  const areBothIntegers =
    Number.isInteger(TBC_RETRY_BASE_DELAY_MS) &&
    Number.isInteger(TBC_RETRY_MAX_DELAY_MS);
  if (!areBothIntegers || TBC_RETRY_MAX_DELAY_MS >= TBC_RETRY_BASE_DELAY_MS) {
    return [];
  }
  return [
    {
      variableName: 'TBC_RETRY_MAX_DELAY_MS',
      message:
        'TBC_RETRY_MAX_DELAY_MS must be greater than or equal to TBC_RETRY_BASE_DELAY_MS',
    },
  ];
}

function toGatewayConfig(variables: EnvironmentVariables): GatewayConfig {
  return {
    port: variables.PORT,
    tbc: {
      apiBaseUrl: variables.TBC_API_BASE_URL.replace(
        TRAILING_SLASHES_PATTERN,
        '',
      ),
      oauthAuthorizeUrl: variables.TBC_OAUTH_AUTHORIZE_URL,
      oauthTokenUrl: variables.TBC_OAUTH_TOKEN_URL,
      oauthClientId: variables.TBC_OAUTH_CLIENT_ID,
      oauthRedirectUri: variables.TBC_OAUTH_REDIRECT_URI,
      oauthUiLocale: variables.TBC_OAUTH_UI_LOCALE,
      httpTimeoutMs: variables.TBC_HTTP_TIMEOUT_MS,
      retryMaxAttempts: variables.TBC_RETRY_MAX_ATTEMPTS,
      retryBaseDelayMs: variables.TBC_RETRY_BASE_DELAY_MS,
      retryMaxDelayMs: variables.TBC_RETRY_MAX_DELAY_MS,
    },
    oauth: {
      stateTtlMs: variables.OAUTH_STATE_TTL_MS,
      tokenRefreshMarginMs: variables.OAUTH_TOKEN_REFRESH_MARGIN_MS,
    },
    dataset: {
      xlsxPath: resolve(process.cwd(), variables.DATASET_XLSX_PATH),
    },
  };
}
