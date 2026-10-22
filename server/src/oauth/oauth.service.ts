import { randomUUID } from 'node:crypto';
import { HttpStatus, Injectable } from '@nestjs/common';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../common/problem-details/problem-details.js';
import { Clock } from '../common/runtime/clock.js';
import { GatewayConfig } from '../config/gateway-config.js';
import { TbcClientService } from '../tbc-client/tbc-client.service.js';
import type { UpstreamCallContext } from '../tbc-client/upstream-call-context.js';
import { ConsentTokenStore } from './consent-token.store.js';
import type { OAuthCallbackQueryDto } from './dto/oauth-callback-query.dto.js';
import { PendingAuthorisationStore } from './pending-authorisation.store.js';
import { createPkcePair } from './pkce.js';
import { parseTokenResponse, type IssuedTokens } from './token-response.js';

export const UNAUTHORISED_CONSENT_DETAIL =
  'Consent has not been authorised through this gateway';

const AUTHORISATION_CODE_RESPONSE_TYPE = 'code';
const PKCE_S256_METHOD = 'S256';
const ACCESS_DENIED_OAUTH_ERROR = 'access_denied';

export interface AuthorisedConsent {
  readonly consentId: string;
}

@Injectable()
export class OAuthService {
  private readonly refreshesInFlight = new Map<string, Promise<string>>();

  constructor(
    private readonly tbcClient: TbcClientService,
    private readonly pendingAuthorisations: PendingAuthorisationStore,
    private readonly consentTokens: ConsentTokenStore,
    private readonly clock: Clock,
    private readonly config: GatewayConfig,
  ) {}

  startAuthorisation(consentId: string): string {
    const { codeVerifier, codeChallenge } = createPkcePair();
    const state = randomUUID();
    this.pendingAuthorisations.save(state, { consentId, codeVerifier });
    const authorizeUrl = new URL(this.config.tbc.oauthAuthorizeUrl);
    const parameters = {
      client_id: this.config.tbc.oauthClientId,
      scope: buildConsentScope(consentId),
      response_type: AUTHORISATION_CODE_RESPONSE_TYPE,
      redirect_uri: this.config.tbc.oauthRedirectUri,
      nonce: randomUUID(),
      state,
      code_challenge_method: PKCE_S256_METHOD,
      code_challenge: codeChallenge,
      ui_locales: this.config.tbc.oauthUiLocale,
    };
    for (const [name, value] of Object.entries(parameters)) {
      authorizeUrl.searchParams.set(name, value);
    }
    return authorizeUrl.toString();
  }

  async completeAuthorisation(
    query: OAuthCallbackQueryDto,
    context: UpstreamCallContext,
  ): Promise<AuthorisedConsent> {
    const pending = this.pendingAuthorisations.take(query.state);
    if (pending === undefined) {
      throw createOAuthProblem(
        HttpStatus.BAD_REQUEST,
        PROBLEM_CODE.STATE_INVALID,
        'OAuth state is unknown, expired or already used',
      );
    }
    const code = readAuthorisationCode(query);
    const tokenResponse = await this.tbcClient.exchangeAuthorisationCode(
      { code, codeVerifier: pending.codeVerifier },
      context,
    );
    this.storeIssuedTokens(
      pending.consentId,
      parseTokenResponse(tokenResponse),
    );
    return { consentId: pending.consentId };
  }

  async getAccessToken(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<string> {
    const tokens = this.consentTokens.find(consentId);
    if (tokens === undefined) {
      throw createOAuthProblem(
        HttpStatus.UNAUTHORIZED,
        PROBLEM_CODE.TOKEN_INVALID,
        UNAUTHORISED_CONSENT_DETAIL,
      );
    }
    const refreshDueAtMs =
      tokens.accessTokenExpiresAtMs - this.config.oauth.tokenRefreshMarginMs;
    if (this.clock.nowMs() < refreshDueAtMs) {
      return tokens.accessToken;
    }
    return this.refreshOnce(consentId, tokens.refreshToken, context);
  }

  hasAuthorisedTokens(consentId: string): boolean {
    return this.consentTokens.find(consentId) !== undefined;
  }

  forgetConsent(consentId: string): void {
    this.consentTokens.delete(consentId);
    this.pendingAuthorisations.forgetConsent(consentId);
  }

  // Concurrent readers share one refresh: the bank rotates the refresh token on every use.
  private refreshOnce(
    consentId: string,
    refreshToken: string,
    context: UpstreamCallContext,
  ): Promise<string> {
    const refreshInFlight = this.refreshesInFlight.get(consentId);
    if (refreshInFlight !== undefined) {
      return refreshInFlight;
    }
    const refresh = this.refreshAccessToken(
      consentId,
      refreshToken,
      context,
    ).finally(() => this.refreshesInFlight.delete(consentId));
    this.refreshesInFlight.set(consentId, refresh);
    return refresh;
  }

  private async refreshAccessToken(
    consentId: string,
    refreshToken: string,
    context: UpstreamCallContext,
  ): Promise<string> {
    const tokenResponse = await this.tbcClient
      .refreshAccessToken(refreshToken, context)
      .catch((error: unknown) => this.handleRefreshFailure(consentId, error));
    const issuedTokens = parseTokenResponse(tokenResponse);
    this.storeIssuedTokens(consentId, issuedTokens);
    return issuedTokens.accessToken;
  }

  // A 4xx means the bank revoked the refresh token; 5xx and timeouts are transient and keep the tokens.
  private handleRefreshFailure(consentId: string, error: unknown): never {
    if (
      !(error instanceof ProblemDetailsException) ||
      !isClientErrorStatus(error.problem.status)
    ) {
      throw error;
    }
    this.consentTokens.delete(consentId);
    throw createOAuthProblem(
      HttpStatus.UNAUTHORIZED,
      PROBLEM_CODE.TOKEN_INVALID,
      error.problem.detail,
    );
  }

  private storeIssuedTokens(
    consentId: string,
    issuedTokens: IssuedTokens,
  ): void {
    if (issuedTokens.scope !== buildConsentScope(consentId)) {
      throw createOAuthProblem(
        HttpStatus.BAD_GATEWAY,
        PROBLEM_CODE.UPSTREAM_CONTRACT_VIOLATION,
        'TBC sandbox issued tokens for a scope other than the authorised consent',
      );
    }
    const nowMs = this.clock.nowMs();
    const { refreshTokenLifetimeMs } = issuedTokens;
    this.consentTokens.save(consentId, {
      accessToken: issuedTokens.accessToken,
      refreshToken: issuedTokens.refreshToken,
      accessTokenExpiresAtMs: nowMs + issuedTokens.accessTokenLifetimeMs,
      refreshTokenExpiresAtMs:
        refreshTokenLifetimeMs === undefined
          ? undefined
          : nowMs + refreshTokenLifetimeMs,
    });
  }
}

function buildConsentScope(consentId: string): string {
  return `AIS:${consentId}`;
}

function isClientErrorStatus(status: number): boolean {
  return (
    status >= HttpStatus.BAD_REQUEST &&
    status < HttpStatus.INTERNAL_SERVER_ERROR
  );
}

function readAuthorisationCode(query: OAuthCallbackQueryDto): string {
  if (query.error === ACCESS_DENIED_OAUTH_ERROR) {
    throw createOAuthProblem(
      HttpStatus.FORBIDDEN,
      PROBLEM_CODE.ACCESS_DENIED,
      'The PSU rejected the consent at the bank',
    );
  }
  if (query.error !== undefined) {
    throw createOAuthProblem(
      HttpStatus.BAD_REQUEST,
      query.error.toUpperCase(),
      query.error_description ?? `The bank reported OAuth error ${query.error}`,
    );
  }
  if (query.code === undefined) {
    throw createOAuthProblem(
      HttpStatus.BAD_REQUEST,
      PROBLEM_CODE.FORMAT_ERROR,
      'OAuth callback must carry either code or error',
    );
  }
  return query.code;
}

function createOAuthProblem(
  status: HttpStatus,
  code: string,
  detail: string,
): ProblemDetailsException {
  return new ProblemDetailsException(createProblem({ status, code, detail }));
}
