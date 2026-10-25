import { Injectable } from '@nestjs/common';
import { OPEN_BANKING_HEADER } from '../common/open-banking-headers.js';
import { GatewayConfig } from '../config/gateway-config.js';
import { JSON_MEDIA_TYPE, TbcHttpTransport } from './tbc-http-transport.js';
import type {
  UpstreamAuthorisation,
  UpstreamCallContext,
  UpstreamTransactionQuery,
} from './upstream-call-context.js';

const FORM_MEDIA_TYPE = 'application/x-www-form-urlencoded';
const TPP_REDIRECT_URI_HEADER = 'TPP-Redirect-URI';
const TPP_REDIRECT_PREFERRED_HEADER = 'TPP-Redirect-Preferred';

export interface AuthorisationCodeGrant {
  readonly code: string;
  readonly codeVerifier: string;
}

type QueryParameters = Readonly<Record<string, string | undefined>>;

interface AccountResourceRequest {
  readonly operationName: string;
  readonly pathSegments: readonly string[];
  readonly queryParameters: QueryParameters;
  readonly authorisation: UpstreamAuthorisation;
  readonly context: UpstreamCallContext;
}

// Callers validate the returned bodies against their DTOs; this class only speaks HTTP.
@Injectable()
export class TbcClientService {
  constructor(
    private readonly transport: TbcHttpTransport,
    private readonly config: GatewayConfig,
  ) {}

  createConsent(
    body: object,
    psuId: string | undefined,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    const psuIdHeaders: Record<string, string> =
      psuId === undefined ? {} : { [OPEN_BANKING_HEADER.PSU_ID]: psuId };
    return this.transport.send({
      operationName: 'createConsent',
      method: 'POST',
      url: this.buildApiUrl(['v1', 'consents']),
      headers: {
        ...buildPsuHeaders(context),
        ...psuIdHeaders,
        'Content-Type': JSON_MEDIA_TYPE,
        [TPP_REDIRECT_URI_HEADER]: this.config.tbc.oauthRedirectUri,
        [TPP_REDIRECT_PREFERRED_HEADER]: 'true',
      },
      body: JSON.stringify(body),
      context,
    });
  }

  getConsent(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.transport.send({
      operationName: 'getConsent',
      method: 'GET',
      url: this.buildApiUrl(['v1', 'consents', consentId]),
      headers: buildPsuHeaders(context),
      context,
    });
  }

  getConsentStatus(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.transport.send({
      operationName: 'getConsentStatus',
      method: 'GET',
      url: this.buildApiUrl(['v1', 'consents', consentId, 'status']),
      headers: buildPsuHeaders(context),
      context,
    });
  }

  async deleteConsent(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<void> {
    await this.transport.send({
      operationName: 'deleteConsent',
      method: 'DELETE',
      url: this.buildApiUrl(['v1', 'consents', consentId]),
      headers: buildPsuHeaders(context),
      context,
    });
  }

  exchangeAuthorisationCode(
    { code, codeVerifier }: AuthorisationCodeGrant,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.requestToken(
      'exchangeAuthorisationCode',
      {
        client_id: this.config.tbc.oauthClientId,
        grant_type: 'authorization_code',
        code,
        code_verifier: codeVerifier,
        redirect_uri: this.config.tbc.oauthRedirectUri,
      },
      context,
    );
  }

  refreshAccessToken(
    refreshToken: string,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.requestToken(
      'refreshAccessToken',
      {
        client_id: this.config.tbc.oauthClientId,
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
      },
      context,
    );
  }

  listAccounts(
    authorisation: UpstreamAuthorisation,
    withBalance: boolean,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.readAccountResource({
      operationName: 'listAccounts',
      pathSegments: ['v1', 'accounts'],
      queryParameters: buildWithBalanceQuery(withBalance),
      authorisation,
      context,
    });
  }

  readAccountDetails(
    authorisation: UpstreamAuthorisation,
    accountId: string,
    withBalance: boolean,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.readAccountResource({
      operationName: 'readAccountDetails',
      pathSegments: ['v1', 'accounts', accountId],
      queryParameters: buildWithBalanceQuery(withBalance),
      authorisation,
      context,
    });
  }

  readBalances(
    authorisation: UpstreamAuthorisation,
    accountId: string,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.readAccountResource({
      operationName: 'readBalances',
      pathSegments: ['v1', 'accounts', accountId, 'balances'],
      queryParameters: {},
      authorisation,
      context,
    });
  }

  readTransactions(
    authorisation: UpstreamAuthorisation,
    accountId: string,
    query: UpstreamTransactionQuery,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.readAccountResource({
      operationName: 'readTransactions',
      pathSegments: ['v1', 'accounts', accountId, 'transactions'],
      queryParameters: {
        dateFrom: query.dateFrom,
        dateTo: query.dateTo,
        bookingStatus: query.bookingStatus,
      },
      authorisation,
      context,
    });
  }

  private readAccountResource(
    resourceRequest: AccountResourceRequest,
  ): Promise<unknown> {
    const { authorisation, context } = resourceRequest;
    return this.transport.send({
      operationName: resourceRequest.operationName,
      method: 'GET',
      url: this.buildApiUrl(
        resourceRequest.pathSegments,
        resourceRequest.queryParameters,
      ),
      headers: {
        ...buildPsuHeaders(context),
        [OPEN_BANKING_HEADER.CONSENT_ID]: authorisation.consentId,
        Authorization: `Bearer ${authorisation.accessToken}`,
      },
      context,
    });
  }

  private requestToken(
    operationName: string,
    formFields: Readonly<Record<string, string>>,
    context: UpstreamCallContext,
  ): Promise<unknown> {
    return this.transport.send({
      operationName,
      method: 'POST',
      url: this.config.tbc.oauthTokenUrl,
      headers: { ...buildPsuHeaders(context), 'Content-Type': FORM_MEDIA_TYPE },
      body: new URLSearchParams(formFields).toString(),
      context,
    });
  }

  private buildApiUrl(
    pathSegments: readonly string[],
    queryParameters: QueryParameters = {},
  ): string {
    const path = pathSegments.map(encodeURIComponent).join('/');
    const query = new URLSearchParams();
    for (const [name, value] of Object.entries(queryParameters)) {
      if (value !== undefined) {
        query.append(name, value);
      }
    }
    const queryText = query.toString();
    const url = `${this.config.tbc.apiBaseUrl}/${path}`;
    return queryText === '' ? url : `${url}?${queryText}`;
  }
}

function buildPsuHeaders(context: UpstreamCallContext): Record<string, string> {
  return context.psuIpAddress === undefined
    ? {}
    : { [OPEN_BANKING_HEADER.PSU_IP_ADDRESS]: context.psuIpAddress };
}

function buildWithBalanceQuery(withBalance: boolean): QueryParameters {
  return withBalance ? { withBalance: 'true' } : {};
}
