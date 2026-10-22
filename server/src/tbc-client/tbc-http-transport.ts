import { randomUUID } from 'node:crypto';
import { HttpStatus, Inject, Injectable, Logger } from '@nestjs/common';
import { OPEN_BANKING_HEADER } from '../common/open-banking-headers.js';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
  type ProblemDetails,
} from '../common/problem-details/problem-details.js';
import { Clock } from '../common/runtime/clock.js';
import { Sleeper } from '../common/runtime/sleeper.js';
import { GatewayConfig } from '../config/gateway-config.js';
import { FETCH, type FetchFunction } from './fetch.token.js';
import {
  RetryPolicy,
  isServerErrorStatus,
  type AttemptOutcome,
  type UpstreamHttpMethod,
} from './retry-policy.js';
import type { UpstreamCallContext } from './upstream-call-context.js';
import { parseUpstreamProblem } from './upstream-problem.js';

export const JSON_MEDIA_TYPE = 'application/json';

const TIMEOUT_ERROR_NAMES = new Set(['TimeoutError', 'AbortError']);
const FIRST_STATUS_AFTER_SUCCESS = 300;

export interface TbcHttpRequest {
  readonly operationName: string;
  readonly method: UpstreamHttpMethod;
  readonly url: string;
  readonly headers: Readonly<Record<string, string>>;
  readonly body?: string;
  readonly context: UpstreamCallContext;
}

interface CompletedAttempt {
  readonly outcome: AttemptOutcome;
  readonly upstreamRequestId: string;
  readonly durationMs: number;
}

@Injectable()
export class TbcHttpTransport {
  private readonly logger = new Logger(TbcHttpTransport.name);

  constructor(
    @Inject(FETCH) private readonly fetchFunction: FetchFunction,
    private readonly config: GatewayConfig,
    private readonly retryPolicy: RetryPolicy,
    private readonly sleeper: Sleeper,
    private readonly clock: Clock,
  ) {}

  send(request: TbcHttpRequest): Promise<unknown> {
    return this.sendAttempt(request, 1);
  }

  private async sendAttempt(
    request: TbcHttpRequest,
    attemptNumber: number,
  ): Promise<unknown> {
    const attempt = await this.performAttempt(request);
    const shouldRetry = this.retryPolicy.shouldRetry(
      request.method,
      attempt.outcome,
      attemptNumber,
    );
    const retryDelayMs = shouldRetry
      ? this.retryPolicy.computeDelayMs(attemptNumber)
      : undefined;
    this.logAttempt(request, attemptNumber, attempt, retryDelayMs);
    if (retryDelayMs === undefined) {
      return this.toResult(request, attempt.outcome, attemptNumber);
    }
    await this.sleeper.sleep(retryDelayMs);
    return this.sendAttempt(request, attemptNumber + 1);
  }

  private async performAttempt(
    request: TbcHttpRequest,
  ): Promise<CompletedAttempt> {
    const upstreamRequestId = randomUUID();
    const startedAtMs = this.clock.nowMs();
    const outcome = await this.fetchOutcome(request, upstreamRequestId);
    const durationMs = this.clock.nowMs() - startedAtMs;
    return { outcome, upstreamRequestId, durationMs };
  }

  private async fetchOutcome(
    request: TbcHttpRequest,
    upstreamRequestId: string,
  ): Promise<AttemptOutcome> {
    try {
      const response = await this.fetchFunction(request.url, {
        method: request.method,
        headers: {
          ...request.headers,
          [OPEN_BANKING_HEADER.REQUEST_ID]: upstreamRequestId,
          Accept: JSON_MEDIA_TYPE,
        },
        body: request.body,
        signal: AbortSignal.timeout(this.config.tbc.httpTimeoutMs),
      });
      return {
        kind: 'response',
        status: response.status,
        bodyText: await response.text(),
      };
    } catch (error) {
      if (error instanceof Error && TIMEOUT_ERROR_NAMES.has(error.name)) {
        return { kind: 'timeout' };
      }
      // fetch reports DNS failures, refused connections and resets as TypeError.
      if (error instanceof TypeError) {
        return { kind: 'transport-error' };
      }
      throw error;
    }
  }

  // Path ids, query strings, headers and bodies stay out of the log: they carry consent ids and tokens.
  private logAttempt(
    request: TbcHttpRequest,
    attemptNumber: number,
    attempt: CompletedAttempt,
    retryDelayMs: number | undefined,
  ): void {
    const maxAttempts = this.retryPolicy.maxAttemptsFor(request.method);
    const result =
      attempt.outcome.kind === 'response'
        ? `status ${attempt.outcome.status}`
        : attempt.outcome.kind;
    const retryNote =
      retryDelayMs === undefined
        ? ''
        : `, retrying in ${Math.round(retryDelayMs)} ms`;
    const line =
      `${request.operationName} attempt ${attemptNumber}/${maxAttempts}` +
      ` upstreamRequestId=${attempt.upstreamRequestId}` +
      ` gatewayRequestId=${request.context.gatewayRequestId}` +
      ` ${result} in ${attempt.durationMs} ms${retryNote}`;
    if (isFailedOutcome(attempt.outcome)) {
      this.logger.warn(line);
    } else {
      this.logger.log(line);
    }
  }

  private toResult(
    request: TbcHttpRequest,
    outcome: AttemptOutcome,
    attemptCount: number,
  ): unknown {
    switch (outcome.kind) {
      case 'response':
        return readResponse(request.operationName, outcome, attemptCount);
      case 'timeout':
        throw new ProblemDetailsException(
          createProblem({
            status: HttpStatus.GATEWAY_TIMEOUT,
            code: PROBLEM_CODE.UPSTREAM_TIMEOUT,
            detail: `TBC sandbox did not answer ${request.operationName} within ${this.config.tbc.httpTimeoutMs} ms ${describeAttemptCount(attemptCount)}`,
          }),
        );
      case 'transport-error':
        throw new ProblemDetailsException(
          createProblem({
            status: HttpStatus.BAD_GATEWAY,
            code: PROBLEM_CODE.SERVICE_UNAVAILABLE,
            detail: `TBC sandbox could not be reached for ${request.operationName}`,
          }),
        );
    }
  }
}

function isFailedOutcome(outcome: AttemptOutcome): boolean {
  return outcome.kind !== 'response' || isServerErrorStatus(outcome.status);
}

function isSuccessStatus(status: number): boolean {
  return status >= HttpStatus.OK && status < FIRST_STATUS_AFTER_SUCCESS;
}

function describeAttemptCount(attemptCount: number): string {
  return attemptCount === 1
    ? '(after 1 attempt)'
    : `(after ${attemptCount} attempts)`;
}

function readResponse(
  operationName: string,
  outcome: Extract<AttemptOutcome, { kind: 'response' }>,
  attemptCount: number,
): unknown {
  if (!isSuccessStatus(outcome.status)) {
    const upstreamProblem = parseUpstreamProblem(
      outcome.status,
      outcome.bodyText,
    );
    throw new ProblemDetailsException(
      toGatewayProblem(upstreamProblem, attemptCount),
    );
  }
  if (outcome.bodyText === '') {
    return undefined;
  }
  return parseJsonBody(operationName, outcome.bodyText);
}

// Upstream 4xx are the caller's business and pass through; upstream 5xx mean the gateway's upstream failed.
function toGatewayProblem(
  upstreamProblem: ProblemDetails,
  attemptCount: number,
): ProblemDetails {
  if (!isServerErrorStatus(upstreamProblem.status)) {
    return upstreamProblem;
  }
  return createProblem({
    status: HttpStatus.BAD_GATEWAY,
    code: upstreamProblem.code,
    detail: `${upstreamProblem.detail} ${describeAttemptCount(attemptCount)}`,
  });
}

function parseJsonBody(operationName: string, bodyText: string): unknown {
  try {
    const body: unknown = JSON.parse(bodyText);
    return body;
  } catch (error) {
    if (!(error instanceof SyntaxError)) {
      throw error;
    }
    throw new ProblemDetailsException(
      createProblem({
        status: HttpStatus.BAD_GATEWAY,
        code: PROBLEM_CODE.UPSTREAM_CONTRACT_VIOLATION,
        detail: `TBC sandbox answered ${operationName} with a body that is not valid JSON`,
      }),
    );
  }
}
