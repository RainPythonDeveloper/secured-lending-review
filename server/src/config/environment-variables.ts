import { Expose, Transform } from 'class-transformer';
import {
  IsDefined,
  IsIn,
  IsInt,
  IsNotEmpty,
  IsString,
  IsUrl,
  Max,
  MaxLength,
  Min,
} from 'class-validator';
import { OAUTH_UI_LOCALES, type OAuthUiLocale } from './gateway-config.js';

export const DEFAULT_PORT = 3000;
export const DEFAULT_TBC_OAUTH_UI_LOCALE: OAuthUiLocale = 'en';
export const DEFAULT_TBC_HTTP_TIMEOUT_MS = 8_000;
export const DEFAULT_TBC_RETRY_MAX_ATTEMPTS = 3;
export const DEFAULT_TBC_RETRY_BASE_DELAY_MS = 250;
export const DEFAULT_TBC_RETRY_MAX_DELAY_MS = 2_000;
export const DEFAULT_OAUTH_STATE_TTL_MS = 600_000;
export const DEFAULT_OAUTH_TOKEN_REFRESH_MARGIN_MS = 60_000;

const MIN_PORT = 1;
const MAX_PORT = 65_535;
const MAX_OAUTH_CLIENT_ID_LENGTH = 128;
const MIN_HTTP_TIMEOUT_MS = 100;
const MAX_HTTP_TIMEOUT_MS = 60_000;
const MIN_RETRY_ATTEMPTS = 1;
// CLAUDE.md §8 caps sandbox calls at three attempts in total.
const MAX_RETRY_ATTEMPTS = 3;
const MAX_RETRY_BASE_DELAY_MS = 10_000;
const MAX_RETRY_DELAY_MS = 30_000;
const MIN_OAUTH_STATE_TTL_MS = 10_000;
const MAX_OAUTH_STATE_TTL_MS = 3_600_000;
const MAX_OAUTH_TOKEN_REFRESH_MARGIN_MS = 600_000;

const INTEGER_TEXT_PATTERN = /^-?\d+$/;
const REQUIRED_MESSAGE = '$property is required';
const HTTP_URL_OPTIONS = {
  protocols: ['http', 'https'],
  require_protocol: true,
};

function isUnset(value: unknown): boolean {
  return value === undefined || value === '';
}

// Non-integer text is passed through unchanged so that @IsInt reports it.
function IntegerOrDefault(defaultValue: number): PropertyDecorator {
  return Transform(({ value }: { value: unknown }) => {
    if (isUnset(value)) {
      return defaultValue;
    }
    return typeof value === 'string' && INTEGER_TEXT_PATTERN.test(value)
      ? Number(value)
      : value;
  });
}

function TextOrDefault(defaultValue: string): PropertyDecorator {
  return Transform(({ value }: { value: unknown }) =>
    isUnset(value) ? defaultValue : value,
  );
}

export class EnvironmentVariables {
  @Expose()
  @IntegerOrDefault(DEFAULT_PORT)
  @IsInt()
  @Min(MIN_PORT)
  @Max(MAX_PORT)
  PORT: number;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsUrl(HTTP_URL_OPTIONS)
  TBC_API_BASE_URL: string;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsUrl(HTTP_URL_OPTIONS)
  TBC_OAUTH_AUTHORIZE_URL: string;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsUrl(HTTP_URL_OPTIONS)
  TBC_OAUTH_TOKEN_URL: string;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsString()
  @IsNotEmpty()
  @MaxLength(MAX_OAUTH_CLIENT_ID_LENGTH)
  TBC_OAUTH_CLIENT_ID: string;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsUrl({ ...HTTP_URL_OPTIONS, require_tld: false })
  TBC_OAUTH_REDIRECT_URI: string;

  @Expose()
  @TextOrDefault(DEFAULT_TBC_OAUTH_UI_LOCALE)
  @IsIn(OAUTH_UI_LOCALES)
  TBC_OAUTH_UI_LOCALE: OAuthUiLocale;

  @Expose()
  @IntegerOrDefault(DEFAULT_TBC_HTTP_TIMEOUT_MS)
  @IsInt()
  @Min(MIN_HTTP_TIMEOUT_MS)
  @Max(MAX_HTTP_TIMEOUT_MS)
  TBC_HTTP_TIMEOUT_MS: number;

  @Expose()
  @IntegerOrDefault(DEFAULT_TBC_RETRY_MAX_ATTEMPTS)
  @IsInt()
  @Min(MIN_RETRY_ATTEMPTS)
  @Max(MAX_RETRY_ATTEMPTS)
  TBC_RETRY_MAX_ATTEMPTS: number;

  @Expose()
  @IntegerOrDefault(DEFAULT_TBC_RETRY_BASE_DELAY_MS)
  @IsInt()
  @Min(0)
  @Max(MAX_RETRY_BASE_DELAY_MS)
  TBC_RETRY_BASE_DELAY_MS: number;

  @Expose()
  @IntegerOrDefault(DEFAULT_TBC_RETRY_MAX_DELAY_MS)
  @IsInt()
  @Min(0)
  @Max(MAX_RETRY_DELAY_MS)
  TBC_RETRY_MAX_DELAY_MS: number;

  @Expose()
  @IntegerOrDefault(DEFAULT_OAUTH_STATE_TTL_MS)
  @IsInt()
  @Min(MIN_OAUTH_STATE_TTL_MS)
  @Max(MAX_OAUTH_STATE_TTL_MS)
  OAUTH_STATE_TTL_MS: number;

  @Expose()
  @IntegerOrDefault(DEFAULT_OAUTH_TOKEN_REFRESH_MARGIN_MS)
  @IsInt()
  @Min(0)
  @Max(MAX_OAUTH_TOKEN_REFRESH_MARGIN_MS)
  OAUTH_TOKEN_REFRESH_MARGIN_MS: number;

  @Expose()
  @IsDefined({ message: REQUIRED_MESSAGE })
  @IsString()
  @IsNotEmpty()
  DATASET_XLSX_PATH: string;
}
