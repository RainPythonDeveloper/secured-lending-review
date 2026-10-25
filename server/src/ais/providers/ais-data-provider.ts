import type { DataSource } from '../../common/data-source/data-source.js';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import type { AccountDetailsResponseDto } from '../accounts/dto/account-details-response.dto.js';
import type { AccountListDto } from '../accounts/dto/account-list.dto.js';
import type { ReadAccountBalanceResponseDto } from '../balances/dto/read-account-balance-response.dto.js';
import type { BookingStatus } from '../shared/ais-formats.js';
import type { TransactionsResponseDto } from '../transactions/dto/transactions-response.dto.js';

export interface AisReadContext extends UpstreamCallContext {
  readonly consentId: string;
}

// Dates are inclusive ISO dates (YYYY-MM-DD).
export interface TransactionListQuery {
  readonly dateFrom?: string;
  readonly dateTo?: string;
  readonly bookingStatus: BookingStatus;
}

export interface AisDataProvider {
  readonly dataSource: DataSource;

  listAccounts(
    context: AisReadContext,
    withBalance: boolean,
  ): Promise<AccountListDto>;

  readAccountDetails(
    context: AisReadContext,
    accountId: string,
    withBalance: boolean,
  ): Promise<AccountDetailsResponseDto>;

  readBalances(
    context: AisReadContext,
    accountId: string,
  ): Promise<ReadAccountBalanceResponseDto>;

  readTransactions(
    context: AisReadContext,
    accountId: string,
    query: TransactionListQuery,
  ): Promise<TransactionsResponseDto>;
}
