import { HttpException, HttpStatus } from '@nestjs/common';

export const PROBLEM_TYPE_BLANK = 'about:blank';
export const PROBLEM_JSON_MEDIA_TYPE = 'application/problem+json';
export const PROBLEM_JSON_CONTENT_TYPE = `${PROBLEM_JSON_MEDIA_TYPE}; charset=utf-8`;

export const PROBLEM_CODE = {
  FORMAT_ERROR: 'FORMAT_ERROR',
  RESOURCE_UNKNOWN: 'RESOURCE_UNKNOWN',
  TOKEN_INVALID: 'TOKEN_INVALID',
  CONSENT_INVALID: 'CONSENT_INVALID',
  STATE_INVALID: 'STATE_INVALID',
  ACCESS_DENIED: 'ACCESS_DENIED',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  UPSTREAM_TIMEOUT: 'UPSTREAM_TIMEOUT',
  UPSTREAM_CONTRACT_VIOLATION: 'UPSTREAM_CONTRACT_VIOLATION',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
} as const;

export type TppMessageCategory = 'ERROR' | 'WARNING';

export interface TppMessage {
  readonly category: TppMessageCategory;
  readonly code: string;
  readonly text: string;
}

export interface ProblemDetails {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly code: string;
  readonly detail: string;
  readonly tppMessages: readonly TppMessage[];
}

export interface ProblemInit {
  readonly status: number;
  readonly code: string;
  readonly detail: string;
}

export class ProblemDetailsException extends HttpException {
  constructor(readonly problem: ProblemDetails) {
    super(problem, problem.status);
  }
}

export function createTppError(code: string, text: string): TppMessage {
  return { category: 'ERROR', code, text };
}

export function createProblem({
  status,
  code,
  detail,
}: ProblemInit): ProblemDetails {
  return {
    type: PROBLEM_TYPE_BLANK,
    title: code,
    status,
    code,
    detail,
    tppMessages: [createTppError(code, detail)],
  };
}

export function describeHttpStatus(status: number): string {
  return HttpStatus[status] ?? `HTTP_${status}`;
}
