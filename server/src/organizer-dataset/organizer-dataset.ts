import type {
  AccountRecord,
  CustomerRecord,
  OrganizerDatasetRecords,
  TransactionRecord,
} from './dataset-records.js';
import { formatMinorUnits } from './minor-units.js';
import { OrganizerDatasetIntegrityError } from './organizer-dataset-errors.js';

// TBC serves savings and deposits through the v2 API, so v1 AIS exposes current accounts only.
const PAYMENT_ACCOUNT_TYPE = 'current';

export interface OrganizerDatasetCounts {
  readonly customers: number;
  readonly accounts: number;
  readonly transactions: number;
}

export class OrganizerDataset {
  readonly counts: OrganizerDatasetCounts;
  readonly coverageEndDate: string;
  private readonly customersById: ReadonlyMap<string, CustomerRecord>;
  private readonly accountsById: ReadonlyMap<string, AccountRecord>;
  private readonly transactionsByAccountId: ReadonlyMap<
    string,
    readonly TransactionRecord[]
  >;

  private constructor(records: OrganizerDatasetRecords) {
    this.customersById = new Map(
      records.customers.map((customer) => [customer.customerId, customer]),
    );
    this.accountsById = new Map(
      records.accounts.map((account) => [account.accountId, account]),
    );
    verifyTransactionAccounts(records.transactions, this.accountsById);
    this.transactionsByAccountId = groupTransactionsByAccount(
      records.transactions,
    );
    verifyClosingBalances(records.accounts, this.transactionsByAccountId);
    this.coverageEndDate = findCoverageEndDate(records.transactions);
    this.counts = {
      customers: records.customers.length,
      accounts: records.accounts.length,
      transactions: records.transactions.length,
    };
  }

  static fromRecords(records: OrganizerDatasetRecords): OrganizerDataset {
    return new OrganizerDataset(records);
  }

  hasCustomer(customerId: string): boolean {
    return this.customersById.has(customerId);
  }

  findCustomer(customerId: string): CustomerRecord | undefined {
    return this.customersById.get(customerId);
  }

  listPaymentAccounts(customerId: string): AccountRecord[] {
    return [...this.accountsById.values()]
      .filter(
        (account) =>
          account.customerId === customerId &&
          account.accountType === PAYMENT_ACCOUNT_TYPE,
      )
      .sort((first, second) => compareText(first.accountId, second.accountId));
  }

  findAccount(accountId: string): AccountRecord | undefined {
    return this.accountsById.get(accountId);
  }

  listTransactions(accountId: string): readonly TransactionRecord[] {
    return this.transactionsByAccountId.get(accountId) ?? [];
  }
}

function verifyTransactionAccounts(
  transactions: readonly TransactionRecord[],
  accountsById: ReadonlyMap<string, AccountRecord>,
): void {
  for (const transaction of transactions) {
    const account = accountsById.get(transaction.accountId);
    if (account === undefined) {
      throw new OrganizerDatasetIntegrityError(
        `Transaction ${transaction.transactionId} belongs to unknown account ${transaction.accountId}`,
      );
    }
    if (account.currency !== transaction.currency) {
      throw new OrganizerDatasetIntegrityError(
        `Transaction ${transaction.transactionId} is in ${transaction.currency} but account ${account.accountId} is in ${account.currency}`,
      );
    }
  }
}

function groupTransactionsByAccount(
  transactions: readonly TransactionRecord[],
): Map<string, TransactionRecord[]> {
  const transactionsByAccountId = new Map<string, TransactionRecord[]>();
  for (const transaction of [...transactions].sort(compareBookingOrder)) {
    const accountTransactions =
      transactionsByAccountId.get(transaction.accountId) ?? [];
    accountTransactions.push(transaction);
    transactionsByAccountId.set(transaction.accountId, accountTransactions);
  }
  return transactionsByAccountId;
}

function compareBookingOrder(
  first: TransactionRecord,
  second: TransactionRecord,
): number {
  return (
    compareText(first.bookingDate, second.bookingDate) ||
    first.postingSequence - second.postingSequence
  );
}

// Ids and ISO dates sort by code unit; locale-aware comparison would make the order depend on ICU data.
function compareText(first: string, second: string): number {
  if (first === second) {
    return 0;
  }
  return first < second ? -1 : 1;
}

function verifyClosingBalances(
  accounts: readonly AccountRecord[],
  transactionsByAccountId: ReadonlyMap<string, readonly TransactionRecord[]>,
): void {
  for (const account of accounts) {
    const transactions = transactionsByAccountId.get(account.accountId) ?? [];
    const movementMinorUnits = transactions.reduce(
      (total, transaction) => total + transaction.amountMinorUnits,
      0,
    );
    const expectedClosingMinorUnits =
      account.openingBalanceMinorUnits + movementMinorUnits;
    if (expectedClosingMinorUnits !== account.closingBalanceMinorUnits) {
      throw new OrganizerDatasetIntegrityError(
        `Account ${account.accountId} does not reconcile: opening ${formatMinorUnits(account.openingBalanceMinorUnits)} ` +
          `plus transactions ${formatMinorUnits(movementMinorUnits)} is not closing ${formatMinorUnits(account.closingBalanceMinorUnits)}`,
      );
    }
  }
}

function findCoverageEndDate(
  transactions: readonly TransactionRecord[],
): string {
  const bookingDates = transactions.map(
    (transaction) => transaction.bookingDate,
  );
  if (bookingDates.length === 0) {
    throw new OrganizerDatasetIntegrityError(
      'Organizer dataset has no transactions, so its coverage period is unknown',
    );
  }
  return bookingDates.reduce((latest, bookingDate) =>
    bookingDate > latest ? bookingDate : latest,
  );
}
