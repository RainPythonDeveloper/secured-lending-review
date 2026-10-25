import { Injectable } from '@nestjs/common';

export interface StoredConsentTokens {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly accessTokenExpiresAtMs: number;
  readonly refreshTokenExpiresAtMs?: number;
}

// Tokens never leave this store through a response or a log line; callers only get them for upstream calls.
@Injectable()
export class ConsentTokenStore {
  private readonly tokensByConsentId = new Map<string, StoredConsentTokens>();

  save(consentId: string, tokens: StoredConsentTokens): void {
    this.tokensByConsentId.set(consentId, tokens);
  }

  find(consentId: string): StoredConsentTokens | undefined {
    return this.tokensByConsentId.get(consentId);
  }

  delete(consentId: string): void {
    this.tokensByConsentId.delete(consentId);
  }
}
