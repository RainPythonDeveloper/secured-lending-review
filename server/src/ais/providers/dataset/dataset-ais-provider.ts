import { HttpStatus, Injectable } from '@nestjs/common';
import {
  ORGANIZER_DATASET_DATA_SOURCE,
  type DataSource,
} from '../../../common/data-source/data-source.js';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../../../common/problem-details/problem-details.js';
import {
  OAuthService,
  UNAUTHORISED_CONSENT_DETAIL,
} from '../../../oauth/oauth.service.js';
import type {
  AccountRecord,
  CustomerRecord,
  TransactionRecord,
} from '../../../organizer-dataset/dataset-records.js';
import { OrganizerDataset } from '../../../organizer-dataset/organizer-dataset.js';
import { buildSyntheticIban } from '../../../organizer-dataset/synthetic-iban.js';
import { TbcClientService } from '../../../tbc-client/tbc-client.service.js';
import { parseUpstreamPayload } from '../../../tbc-client/upstream-payload.js';
import type { AccountDetailsDto } from '../../accounts/dto/account-details.dto.js';
import type { AccountDetailsResponseDto } from '../../accounts/dto/account-details-response.dto.js';
import type { AccountListDto } from '../../accounts/dto/account-list.dto.js';
import type { ReadAccountBalanceResponseDto } from '../../balances/dto/read-account-balance-response.dto.js';
import { ConsentDetailsResponseDto } from '../../consents/dto/consent-details-response.dto.js';
import type { ConsentStatus } from '../../shared/ais-formats.js';
import type { AccountAccessDto } from '../../shared/dto/account-access.dto.js';
import type { TransactionDto } from '../../transactions/dto/transaction.dto.js';
import type {
  AccountReportDto,
  TransactionsResponseDto,
} from '../../transactions/dto/transactions-response.dto.js';
import { buildTransactionLinks } from '../account-links.js';
import type {
  AisDataProvider,
  AisReadContext,
  TransactionListQuery,
} from '../ais-data-provider.js';
import { PersonaBindingStore } from '../persona-binding.store.js';
import { isServiceGranted, type AisService } from './consent-access-policy.js';
import {
  mapAccount,
  mapAccountReference,
  mapBalances,
  mapTransaction,
} from './dataset-ais-mapper.js';

const VALID_CONSENT_STATUS: ConsentStatus = 'valid';

interface PersonaReadGrant {
  readonly customer: CustomerRecord;
  readonly access: AccountAccessDto;
}

interface AccountReadGrant extends PersonaReadGrant {
  readonly account: AccountRecord;
}

// Serves persona-bound consents from the organizer dataset while the bank keeps owning the consent,
// so every read enforces the bank's consent status and access scope like the sandbox would.
@Injectable()
export class DatasetAisProvider implements AisDataProvider {
  readonly dataSource: DataSource = ORGANIZER_DATASET_DATA_SOURCE;

  constructor(
    private readonly tbcClient: TbcClientService,
    private readonly oauthService: OAuthService,
    private readonly dataset: OrganizerDataset,
    private readonly bindings: PersonaBindingStore,
  ) {}

  async listAccounts(
    context: AisReadContext,
    withBalance: boolean,
  ): Promise<AccountListDto> {
    const { customer, access } = await this.authorisePersonaRead(context);
    const grantedAccounts = this.dataset
      .listPaymentAccounts(customer.customerId)
      .filter((account) => isAccountGranted(access, 'accounts', account));
    return {
      accounts: grantedAccounts.map((account) =>
        this.mapAccountDetails({ customer, access, account }, withBalance),
      ),
    };
  }

  async readAccountDetails(
    context: AisReadContext,
    accountId: string,
    withBalance: boolean,
  ): Promise<AccountDetailsResponseDto> {
    const grant = await this.authoriseAccountRead(
      context,
      accountId,
      'accounts',
    );
    return { account: this.mapAccountDetails(grant, withBalance) };
  }

  async readBalances(
    context: AisReadContext,
    accountId: string,
  ): Promise<ReadAccountBalanceResponseDto> {
    const { account } = await this.authoriseAccountRead(
      context,
      accountId,
      'balances',
    );
    return {
      account: mapAccountReference(account),
      balances: mapBalances(account, this.dataset.coverageEndDate),
    };
  }

  async readTransactions(
    context: AisReadContext,
    accountId: string,
    query: TransactionListQuery,
  ): Promise<TransactionsResponseDto> {
    const { account } = await this.authoriseAccountRead(
      context,
      accountId,
      'transactions',
    );
    return {
      account: mapAccountReference(account),
      transactions: this.buildAccountReport(account, query),
    };
  }

  private async authorisePersonaRead(
    context: AisReadContext,
  ): Promise<PersonaReadGrant> {
    const customer = this.findBoundCustomer(context.consentId);
    if (!this.oauthService.hasAuthorisedTokens(context.consentId)) {
      throw createDatasetProblem(
        HttpStatus.UNAUTHORIZED,
        PROBLEM_CODE.TOKEN_INVALID,
        UNAUTHORISED_CONSENT_DETAIL,
      );
    }
    const consent = parseUpstreamPayload(
      ConsentDetailsResponseDto,
      await this.tbcClient.getConsent(context.consentId, context),
      'getConsent',
    );
    if (consent.consentStatus !== VALID_CONSENT_STATUS) {
      throw createDatasetProblem(
        HttpStatus.UNAUTHORIZED,
        PROBLEM_CODE.CONSENT_INVALID,
        `Consent is ${consent.consentStatus}`,
      );
    }
    return { customer, access: consent.access };
  }

  private async authoriseAccountRead(
    context: AisReadContext,
    accountId: string,
    service: AisService,
  ): Promise<AccountReadGrant> {
    const personaGrant = await this.authorisePersonaRead(context);
    const account = this.dataset
      .listPaymentAccounts(personaGrant.customer.customerId)
      .find((paymentAccount) => paymentAccount.accountId === accountId);
    if (account === undefined) {
      throw createDatasetProblem(
        HttpStatus.NOT_FOUND,
        PROBLEM_CODE.RESOURCE_UNKNOWN,
        'Account resourceId not found',
      );
    }
    if (!isAccountGranted(personaGrant.access, service, account)) {
      throw createDatasetProblem(
        HttpStatus.FORBIDDEN,
        PROBLEM_CODE.CONSENT_INVALID,
        `Consent does not allow ${service} for this account`,
      );
    }
    return { ...personaGrant, account };
  }

  // AisProviderResolver hands this provider persona-bound consents only, and bindings name dataset customers.
  private findBoundCustomer(consentId: string): CustomerRecord {
    const customerId = this.bindings.findCustomerId(consentId);
    const customer =
      customerId === undefined
        ? undefined
        : this.dataset.findCustomer(customerId);
    if (customer === undefined) {
      throw new Error('Consent is not bound to an organizer dataset customer');
    }
    return customer;
  }

  private mapAccountDetails(
    { customer, access, account }: AccountReadGrant,
    withBalance: boolean,
  ): AccountDetailsDto {
    const balances =
      withBalance && isAccountGranted(access, 'balances', account)
        ? mapBalances(account, this.dataset.coverageEndDate)
        : undefined;
    return mapAccount(account, customer, balances);
  }

  // The organizer dataset has no pending transactions.
  private buildAccountReport(
    account: AccountRecord,
    query: TransactionListQuery,
  ): AccountReportDto {
    const links = buildTransactionLinks(account.accountId);
    switch (query.bookingStatus) {
      case 'booked':
        return {
          booked: this.listBookedTransactions(account, query),
          _links: links,
        };
      case 'pending':
        return { pending: [], _links: links };
      case 'both':
        return {
          booked: this.listBookedTransactions(account, query),
          pending: [],
          _links: links,
        };
    }
  }

  private listBookedTransactions(
    account: AccountRecord,
    query: TransactionListQuery,
  ): TransactionDto[] {
    return this.dataset
      .listTransactions(account.accountId)
      .filter((transaction) => isBookedWithin(transaction, query))
      .map((transaction) =>
        mapTransaction(transaction, this.findRelatedAccount(transaction)),
      );
  }

  private findRelatedAccount(
    transaction: TransactionRecord,
  ): AccountRecord | undefined {
    return transaction.relatedAccountId === null
      ? undefined
      : this.dataset.findAccount(transaction.relatedAccountId);
  }
}

function isAccountGranted(
  access: AccountAccessDto,
  service: AisService,
  account: AccountRecord,
): boolean {
  return isServiceGranted(
    access,
    service,
    buildSyntheticIban(account.accountId),
  );
}

// ISO dates order chronologically as text.
function isBookedWithin(
  transaction: TransactionRecord,
  { dateFrom, dateTo }: TransactionListQuery,
): boolean {
  const { bookingDate } = transaction;
  return (
    (dateFrom === undefined || bookingDate >= dateFrom) &&
    (dateTo === undefined || bookingDate <= dateTo)
  );
}

function createDatasetProblem(
  status: HttpStatus,
  code: string,
  detail: string,
): ProblemDetailsException {
  return new ProblemDetailsException(createProblem({ status, code, detail }));
}
