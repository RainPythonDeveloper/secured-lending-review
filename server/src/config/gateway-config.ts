export const OAUTH_UI_LOCALES = ['en', 'ka'] as const;

export type OAuthUiLocale = (typeof OAUTH_UI_LOCALES)[number];

export interface TbcClientConfig {
  readonly apiBaseUrl: string;
  readonly oauthAuthorizeUrl: string;
  readonly oauthTokenUrl: string;
  readonly oauthClientId: string;
  readonly oauthRedirectUri: string;
  readonly oauthUiLocale: OAuthUiLocale;
  readonly httpTimeoutMs: number;
  readonly retryMaxAttempts: number;
  readonly retryBaseDelayMs: number;
  readonly retryMaxDelayMs: number;
}

export interface OAuthConfig {
  readonly stateTtlMs: number;
  readonly tokenRefreshMarginMs: number;
}

export interface DatasetConfig {
  readonly xlsxPath: string;
}

// An abstract class rather than an interface so that it can serve as the Nest injection token.
export abstract class GatewayConfig {
  abstract readonly port: number;
  abstract readonly tbc: TbcClientConfig;
  abstract readonly oauth: OAuthConfig;
  abstract readonly dataset: DatasetConfig;
}
