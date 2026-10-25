import type { GatewayConfig } from '../config/gateway-config.js';
import { FixedRandomSource } from '../../test/support/fake-runtime.js';
import { testGatewayConfig } from '../../test/support/test-gateway-config.js';
import {
  RetryPolicy,
  type AttemptOutcome,
  type UpstreamHttpMethod,
} from './retry-policy.js';

function upstreamResponse(status: number): AttemptOutcome {
  return { kind: 'response', status, bodyText: '' };
}

function configWithDelays(
  retryBaseDelayMs: number,
  retryMaxDelayMs: number,
): GatewayConfig {
  return {
    port: testGatewayConfig.port,
    tbc: { ...testGatewayConfig.tbc, retryBaseDelayMs, retryMaxDelayMs },
    oauth: testGatewayConfig.oauth,
    dataset: testGatewayConfig.dataset,
  };
}

describe('RetryPolicy', () => {
  const policy = new RetryPolicy(testGatewayConfig, new FixedRandomSource(0));

  it.each<[UpstreamHttpMethod, AttemptOutcome, number, boolean]>([
    ['GET', upstreamResponse(502), 1, true],
    ['GET', upstreamResponse(503), 1, true],
    ['GET', upstreamResponse(500), 1, true],
    ['GET', upstreamResponse(502), 2, true],
    ['GET', { kind: 'timeout' }, 1, true],
    ['GET', upstreamResponse(404), 1, false],
    ['GET', upstreamResponse(401), 1, false],
    ['GET', upstreamResponse(200), 1, false],
    ['GET', { kind: 'transport-error' }, 1, false],
    ['GET', upstreamResponse(502), 3, false],
    ['GET', { kind: 'timeout' }, 3, false],
    ['POST', upstreamResponse(502), 1, false],
    ['POST', { kind: 'timeout' }, 1, false],
    ['DELETE', upstreamResponse(502), 1, false],
  ])(
    'decides for %s after %o on attempt %i that retrying is %s',
    (method, outcome, attemptNumber, expected) => {
      const shouldRetry = policy.shouldRetry(method, outcome, attemptNumber);

      expect(shouldRetry).toBe(expected);
    },
  );

  it.each([
    ['GET', 3],
    ['POST', 1],
    ['DELETE', 1],
  ] as const)('gives %s at most %i attempt(s) in total', (method, expected) => {
    const maxAttempts = policy.maxAttemptsFor(method);

    expect(maxAttempts).toBe(expected);
  });

  it.each([
    [0, 1, 125],
    [0.999, 1, 249.875],
    [0, 2, 250],
    [0.999, 2, 499.75],
  ])(
    'waits within the equal-jitter bounds (random %f, failed attempt %i -> %f ms)',
    (fraction, failedAttemptNumber, expectedDelayMs) => {
      const jitteredPolicy = new RetryPolicy(
        testGatewayConfig,
        new FixedRandomSource(fraction),
      );

      const delayMs = jitteredPolicy.computeDelayMs(failedAttemptNumber);

      expect(delayMs).toBeCloseTo(expectedDelayMs, 6);
    },
  );

  it('caps the backoff ceiling at the maximum delay', () => {
    const cappedPolicy = new RetryPolicy(
      configWithDelays(1500, 2000),
      new FixedRandomSource(0.5),
    );

    const delayMs = cappedPolicy.computeDelayMs(2);

    expect(delayMs).toBe(1500);
  });
});
