import { Injectable } from '@nestjs/common';
import {
  TBC_SANDBOX_DATA_SOURCE,
  type DataSource,
} from '../../../common/data-source/data-source.js';
import { OAuthService } from '../../../oauth/oauth.service.js';
import { TbcClientService } from '../../../tbc-client/tbc-client.service.js';
import type { UpstreamAuthorisation } from '../../../tbc-client/upstream-call-context.js';
import { parseUpstreamPayload } from '../../../tbc-client/upstream-payload.js';
import type { AccountDetailsDto } from '../../accounts/dto/account-details.dto.js';
import { AccountDetailsResponseDto } from '../../accounts/dto/account-details-response.dto.js';
import { AccountListDto } from '../../accounts/dto/account-list.dto.js';
import { ReadAccountBalanceResponseDto } from '../../balances/dto/read-account-balance-response.dto.js';
import { TransactionsResponseDto } from '../../transactions/dto/transactions-response.dto.js';
import { buildAccountLinks, buildTransactionLinks } from '../account-links.js';
import type {
  AisDataProvider,
  AisReadContext,
  TransactionListQuery,
} from '../ais-data-provider.js';

@Injectable()
export class SandboxAisProvider implements AisDataProvider {
  readonly dataSource: DataSource = TBC_SANDBOX_DATA_SOURCE;

  constructor(
    private readonly tbcClient: TbcClientService,
    private readonly oauthService: OAuthService,
  ) {}

  async listAccounts(
    context: AisReadContext,
    withBalance: boolean,
  ): Promise<AccountListDto> {
    const authorisation = await this.authorise(context);
    const accountList = parseUpstreamPayload(
      AccountListDto,
      await this.tbcClient.listAccounts(authorisation, withBalance, context),
      'listAccounts',
    );
    return { accounts: accountList.accounts.map(linkAccountToGateway) };
  }

  async readAccountDetails(
    context: AisReadContext,
    accountId: string,
    withBalance: boolean,
  ): Promise<AccountDetailsResponseDto> {
    const authorisation = await this.authorise(context);
    const accountDetails = parseUpstreamPayload(
      AccountDetailsResponseDto,
      await this.tbcClient.readAccountDetails(
        authorisation,
        accountId,
        withBalance,
        context,
      ),
      'readAccountDetails',
    );
    return { account: linkAccountToGateway(accountDetails.account) };
  }

  async readBalances(
    context: AisReadContext,
    accountId: string,
  ): Promise<ReadAccountBalanceResponseDto> {
    const authorisation = await this.authorise(context);
    return parseUpstreamPayload(
      ReadAccountBalanceResponseDto,
      await this.tbcClient.readBalances(authorisation, accountId, context),
      'readBalances',
    );
  }

  async readTransactions(
    context: AisReadContext,
    accountId: string,
    query: TransactionListQuery,
  ): Promise<TransactionsResponseDto> {
    const authorisation = await this.authorise(context);
    const { account, transactions } = parseUpstreamPayload(
      TransactionsResponseDto,
      await this.tbcClient.readTransactions(
        authorisation,
        accountId,
        query,
        context,
      ),
      'readTransactions',
    );
    return {
      account,
      transactions: {
        booked: transactions.booked,
        pending: transactions.pending,
        _links: buildTransactionLinks(accountId),
      },
    };
  }

  private async authorise(
    context: AisReadContext,
  ): Promise<UpstreamAuthorisation> {
    const accessToken = await this.oauthService.getAccessToken(
      context.consentId,
      context,
    );
    return { consentId: context.consentId, accessToken };
  }
}

// Upstream _links name /0.8 sandbox paths that callers cannot use, so gateway links replace them.
function linkAccountToGateway({
  _links,
  ...account
}: AccountDetailsDto): AccountDetailsDto {
  return { ...account, _links: buildAccountLinks(account.resourceId) };
}
