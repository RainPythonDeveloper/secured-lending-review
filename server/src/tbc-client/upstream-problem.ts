import {
  PROBLEM_CODE,
  createProblem,
  describeHttpStatus,
  type ProblemDetails,
  type TppMessage,
} from '../common/problem-details/problem-details.js';
import { isServerErrorStatus } from './retry-policy.js';

type JsonRecord = Record<string, unknown>;

// Non-2xx bodies come in three shapes: sandbox problem+json, OAuth error JSON, or anything else.
export function parseUpstreamProblem(
  status: number,
  bodyText: string,
): ProblemDetails {
  const body = parseJsonRecord(bodyText);
  return (
    readSandboxProblem(status, body) ??
    readOAuthError(status, body) ??
    createFallbackProblem(status)
  );
}

function parseJsonRecord(bodyText: string): JsonRecord | undefined {
  try {
    const body: unknown = JSON.parse(bodyText);
    return isJsonRecord(body) ? body : undefined;
  } catch (error) {
    if (error instanceof SyntaxError) {
      return undefined;
    }
    throw error;
  }
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readSandboxProblem(
  status: number,
  body: JsonRecord | undefined,
): ProblemDetails | undefined {
  if (typeof body?.code !== 'string' || typeof body.detail !== 'string') {
    return undefined;
  }
  const problem = createProblem({
    status,
    code: body.code,
    detail: body.detail,
  });
  const tppMessages = readTppMessages(body.tppMessages);
  return tppMessages === undefined ? problem : { ...problem, tppMessages };
}

function readTppMessages(value: unknown): TppMessage[] | undefined {
  if (!Array.isArray(value) || value.length === 0) {
    return undefined;
  }
  const tppMessages = value.filter(isTppMessage);
  return tppMessages.length === value.length ? tppMessages : undefined;
}

function isTppMessage(value: unknown): value is TppMessage {
  return (
    isJsonRecord(value) &&
    (value.category === 'ERROR' || value.category === 'WARNING') &&
    typeof value.code === 'string' &&
    typeof value.text === 'string'
  );
}

function readOAuthError(
  status: number,
  body: JsonRecord | undefined,
): ProblemDetails | undefined {
  if (typeof body?.error !== 'string') {
    return undefined;
  }
  const detail =
    typeof body.error_description === 'string'
      ? body.error_description
      : body.error;
  return createProblem({ status, code: body.error.toUpperCase(), detail });
}

function createFallbackProblem(status: number): ProblemDetails {
  const code = isServerErrorStatus(status)
    ? PROBLEM_CODE.SERVICE_UNAVAILABLE
    : describeHttpStatus(status);
  return createProblem({
    status,
    code,
    detail: `TBC sandbox answered HTTP ${status} without problem details`,
  });
}
