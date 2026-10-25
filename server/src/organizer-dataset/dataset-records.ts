export const ACCOUNT_TYPES = ['current', 'savings', 'term_deposit'] as const;
export const ACCOUNT_STATUSES = ['active', 'closed'] as const;

export type AccountType = (typeof ACCOUNT_TYPES)[number];
export type AccountStatus = (typeof ACCOUNT_STATUSES)[number];

export interface CustomerRecord {
  readonly customerId: string;
  readonly fullName: string;
}

export interface AccountRecord {
  readonly accountId: string;
  readonly customerId: string;
  readonly accountType: AccountType;
  readonly currency: string;
  readonly status: AccountStatus;
  readonly openingBalanceMinorUnits: number;
  readonly closingBalanceMinorUnits: number;
}

// Signed amounts as in the workbook: credits are positive, debits negative.
export interface TransactionRecord {
  readonly transactionId: string;
  readonly accountId: string;
  readonly bookingDate: string;
  readonly postingSequence: number;
  readonly currency: string;
  readonly category: string;
  readonly amountMinorUnits: number;
  readonly balanceAfterMinorUnits: number;
  readonly channel: string;
  readonly counterparty: string;
  readonly description: string;
  readonly transferId: string | null;
  readonly relatedAccountId: string | null;
  readonly fxRate: string | null;
}

export interface OrganizerDatasetRecords {
  readonly customers: readonly CustomerRecord[];
  readonly accounts: readonly AccountRecord[];
  readonly transactions: readonly TransactionRecord[];
}
