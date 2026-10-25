import { HttpStatus } from '@nestjs/common';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../common/problem-details/problem-details.js';

export interface IssuedTokens {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly accessTokenLifetimeMs: number;
  readonly refreshTokenLifetimeMs?: number;
  readonly scope: string;
}

type JsonRecord = Record<string, unknown>;

const BEARER_TOKEN_TYPE = 'bearer';
const MS_PER_SECOND = 1_000;
const LIFETIME_SECONDS_TEXT_PATTERN = /^\d+$/;

export function parseTokenResponse(body: unknown): IssuedTokens {
  if (!isJsonRecord(body)) {
    throw createTokenContractViolation('body is not a JSON object');
  }
  requireBearerTokenType(body);
  return {
    accessToken: readNonEmptyString(body, 'access_token'),
    refreshToken: readNonEmptyString(body, 'refresh_token'),
    accessTokenLifetimeMs: readLifetimeMs(body, 'expires_in'),
    refreshTokenLifetimeMs:
      body.refresh_token_expires_in === undefined
        ? undefined
        : readLifetimeMs(body, 'refresh_token_expires_in'),
    scope: readNonEmptyString(body, 'scope'),
  };
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// RFC 6749 §5.1: the token type value is case-insensitive.
function requireBearerTokenType(body: JsonRecord): void {
  const tokenType = body.token_type;
  if (
    typeof tokenType !== 'string' ||
    tokenType.toLowerCase() !== BEARER_TOKEN_TYPE
  ) {
    throw createTokenContractViolation('token_type must be Bearer');
  }
}

function readNonEmptyString(body: JsonRecord, fieldName: string): string {
  const value = body[fieldName];
  if (typeof value !== 'string' || value === '') {
    throw createTokenContractViolation(
      `${fieldName} must be a non-empty string`,
    );
  }
  return value;
}

// The sandbox sends expires_in as a number but refresh_token_expires_in as a digit string.
function readLifetimeMs(body: JsonRecord, fieldName: string): number {
  const value = body[fieldName];
  const lifetimeSeconds =
    typeof value === 'string' && LIFETIME_SECONDS_TEXT_PATTERN.test(value)
      ? Number(value)
      : value;
  if (
    typeof lifetimeSeconds !== 'number' ||
    !Number.isSafeInteger(lifetimeSeconds) ||
    lifetimeSeconds < 0
  ) {
    throw createTokenContractViolation(
      `${fieldName} must be a whole number of seconds`,
    );
  }
  return lifetimeSeconds * MS_PER_SECOND;
}

function createTokenContractViolation(issue: string): ProblemDetailsException {
  return new ProblemDetailsException(
    createProblem({
      status: HttpStatus.BAD_GATEWAY,
      code: PROBLEM_CODE.UPSTREAM_CONTRACT_VIOLATION,
      detail: `TBC sandbox token response does not match the specification: ${issue}`,
    }),
  );
}
