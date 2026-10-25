import { Injectable } from '@nestjs/common';
import { Clock } from '../common/runtime/clock.js';
import { GatewayConfig } from '../config/gateway-config.js';

export interface PendingAuthorisation {
  readonly consentId: string;
  readonly codeVerifier: string;
}

interface StoredPendingAuthorisation extends PendingAuthorisation {
  readonly createdAtMs: number;
}

// PSUs who never return from the bank leave their state behind; save() purges those entries.
@Injectable()
export class PendingAuthorisationStore {
  private readonly pendingByState = new Map<
    string,
    StoredPendingAuthorisation
  >();

  constructor(
    private readonly clock: Clock,
    private readonly config: GatewayConfig,
  ) {}

  get size(): number {
    return this.pendingByState.size;
  }

  save(state: string, pending: PendingAuthorisation): void {
    this.purgeExpired();
    this.pendingByState.set(state, {
      consentId: pending.consentId,
      codeVerifier: pending.codeVerifier,
      createdAtMs: this.clock.nowMs(),
    });
  }

  take(state: string): PendingAuthorisation | undefined {
    const stored = this.pendingByState.get(state);
    this.pendingByState.delete(state);
    if (stored === undefined || this.isExpired(stored)) {
      return undefined;
    }
    return { consentId: stored.consentId, codeVerifier: stored.codeVerifier };
  }

  forgetConsent(consentId: string): void {
    for (const [state, stored] of this.pendingByState) {
      if (stored.consentId === consentId) {
        this.pendingByState.delete(state);
      }
    }
  }

  private purgeExpired(): void {
    for (const [state, stored] of this.pendingByState) {
      if (this.isExpired(stored)) {
        this.pendingByState.delete(state);
      }
    }
  }

  private isExpired(stored: StoredPendingAuthorisation): boolean {
    const ageMs = this.clock.nowMs() - stored.createdAtMs;
    return ageMs > this.config.oauth.stateTtlMs;
  }
}
