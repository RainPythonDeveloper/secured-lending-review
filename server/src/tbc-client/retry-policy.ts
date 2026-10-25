import { HttpStatus, Injectable } from '@nestjs/common';
import { RandomSource } from '../common/runtime/random-source.js';
import { GatewayConfig } from '../config/gateway-config.js';

export type UpstreamHttpMethod = 'GET' | 'POST' | 'DELETE';

export type AttemptOutcome =
  | {
      readonly kind: 'response';
      readonly status: number;
      readonly bodyText: string;
    }
  | { readonly kind: 'timeout' }
  | { readonly kind: 'transport-error' };

const BACKOFF_MULTIPLIER = 2;
const SINGLE_ATTEMPT = 1;
const FIRST_STATUS_AFTER_SERVER_ERRORS = 600;

export function isServerErrorStatus(status: number): boolean {
  return (
    status >= HttpStatus.INTERNAL_SERVER_ERROR &&
    status < FIRST_STATUS_AFTER_SERVER_ERRORS
  );
}

// CLAUDE.md §8: only idempotent GETs are retried, and only after a 5xx or a timeout.
@Injectable()
export class RetryPolicy {
  constructor(
    private readonly config: GatewayConfig,
    private readonly randomSource: RandomSource,
  ) {}

  maxAttemptsFor(method: UpstreamHttpMethod): number {
    return method === 'GET' ? this.config.tbc.retryMaxAttempts : SINGLE_ATTEMPT;
  }

  shouldRetry(
    method: UpstreamHttpMethod,
    outcome: AttemptOutcome,
    attemptNumber: number,
  ): boolean {
    if (attemptNumber >= this.maxAttemptsFor(method)) {
      return false;
    }
    return (
      outcome.kind === 'timeout' ||
      (outcome.kind === 'response' && isServerErrorStatus(outcome.status))
    );
  }

  // Exponential backoff with equal jitter: half of the ceiling is fixed, half is random.
  computeDelayMs(failedAttemptNumber: number): number {
    const { retryBaseDelayMs, retryMaxDelayMs } = this.config.tbc;
    const ceilingMs = Math.min(
      retryMaxDelayMs,
      retryBaseDelayMs * BACKOFF_MULTIPLIER ** (failedAttemptNumber - 1),
    );
    const halfCeilingMs = ceilingMs / 2;
    return halfCeilingMs + this.randomSource.nextFraction() * halfCeilingMs;
  }
}
