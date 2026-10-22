import { FakeClock } from '../../test/support/fake-runtime.js';
import { testGatewayConfig } from '../../test/support/test-gateway-config.js';
import { PendingAuthorisationStore } from './pending-authorisation.store.js';

const STATE = '7c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f';
const OTHER_STATE = '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d';
const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const OTHER_CONSENT_ID = '9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b';
const STATE_TTL_MS = testGatewayConfig.oauth.stateTtlMs;
const pending = { consentId: CONSENT_ID, codeVerifier: 'verifier-1' };

describe('PendingAuthorisationStore', () => {
  let clock: FakeClock;
  let store: PendingAuthorisationStore;

  beforeEach(() => {
    clock = new FakeClock(1_792_670_000_000);
    store = new PendingAuthorisationStore(clock, testGatewayConfig);
  });

  it('returns the pending authorisation saved for a state', () => {
    store.save(STATE, pending);

    const taken = store.take(STATE);

    expect(taken).toEqual(pending);
  });

  it('hands out a state only once', () => {
    store.save(STATE, pending);
    store.take(STATE);

    const takenAgain = store.take(STATE);

    expect(takenAgain).toBeUndefined();
  });

  it('returns nothing for an unknown state', () => {
    const taken = store.take(STATE);

    expect(taken).toBeUndefined();
  });

  it('still accepts a state at the end of its lifetime', () => {
    store.save(STATE, pending);
    clock.advanceBy(STATE_TTL_MS);

    const taken = store.take(STATE);

    expect(taken).toEqual(pending);
  });

  it('rejects a state older than its lifetime', () => {
    store.save(STATE, pending);
    clock.advanceBy(STATE_TTL_MS + 1);

    const taken = store.take(STATE);

    expect(taken).toBeUndefined();
  });

  it('purges expired states when a new state is saved', () => {
    store.save(STATE, pending);
    clock.advanceBy(STATE_TTL_MS + 1);

    store.save(OTHER_STATE, pending);

    expect(store.size).toBe(1);
  });

  it('forgets every pending state of a consent', () => {
    store.save(STATE, pending);
    store.save(OTHER_STATE, {
      consentId: OTHER_CONSENT_ID,
      codeVerifier: 'verifier-2',
    });

    store.forgetConsent(CONSENT_ID);

    expect(store.take(STATE)).toBeUndefined();
    expect(store.take(OTHER_STATE)).toEqual({
      consentId: OTHER_CONSENT_ID,
      codeVerifier: 'verifier-2',
    });
  });
});
