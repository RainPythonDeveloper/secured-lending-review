import { personaRecords } from '../../test/fixtures/organizer-dataset/persona-records.js';
import type {
  AccountRecord,
  OrganizerDatasetRecords,
  TransactionRecord,
} from './dataset-records.js';
import { OrganizerDatasetIntegrityError } from './organizer-dataset-errors.js';
import { OrganizerDataset } from './organizer-dataset.js';

function recordsWith(
  overrides: Partial<OrganizerDatasetRecords>,
): OrganizerDatasetRecords {
  return { ...personaRecords, ...overrides };
}

function transactionIds(transactions: readonly TransactionRecord[]): string[] {
  return transactions.map((transaction) => transaction.transactionId);
}

function accountIds(accounts: readonly AccountRecord[]): string[] {
  return accounts.map((account) => account.accountId);
}

describe('OrganizerDataset', () => {
  const dataset = OrganizerDataset.fromRecords(personaRecords);

  it.each([
    ['CUS-024', true],
    ['CUS-999', false],
  ])('answers whether %s is a dataset customer: %s', (customerId, expected) => {
    expect(dataset.hasCustomer(customerId)).toBe(expected);
  });

  it('finds a customer by id', () => {
    const customer = dataset.findCustomer('CUS-024');

    expect(customer).toEqual({
      customerId: 'CUS-024',
      fullName: 'Levan Gelashvili',
    });
  });

  it('finds an account by id', () => {
    const account = dataset.findAccount('ACC-0143');

    expect(account?.accountType).toBe('savings');
  });

  it.each([
    ['CUS-024', ['ACC-0024']],
    ['CUS-011', ['ACC-0011', 'ACC-0179']],
    ['CUS-999', []],
  ])(
    'lists only the current accounts of %s, sorted by account id',
    (customerId, expectedAccountIds) => {
      const accounts = dataset.listPaymentAccounts(customerId);

      expect(accountIds(accounts)).toEqual(expectedAccountIds);
    },
  );

  it('lists the transactions of an account by booking date and posting sequence', () => {
    const shuffledDataset = OrganizerDataset.fromRecords(
      recordsWith({ transactions: [...personaRecords.transactions].reverse() }),
    );

    const transactions = shuffledDataset.listTransactions('ACC-0179');

    expect(transactionIds(transactions)).toEqual(['TX-0000216', 'TX-0000217']);
  });

  it('lists no transactions for an unknown account', () => {
    const transactions = dataset.listTransactions('ACC-9999');

    expect(transactions).toEqual([]);
  });

  it('reports the latest booking date as the coverage end date', () => {
    expect(dataset.coverageEndDate).toBe('2026-05-08');
  });

  it('counts the records it holds', () => {
    expect(dataset.counts).toEqual({
      customers: 2,
      accounts: 4,
      transactions: 7,
    });
  });

  it('rejects an account whose transactions do not lead to its closing balance', () => {
    const records = recordsWith({
      accounts: personaRecords.accounts.map((account) =>
        account.accountId === 'ACC-0024'
          ? { ...account, closingBalanceMinorUnits: 181963 }
          : account,
      ),
    });

    expect(() => OrganizerDataset.fromRecords(records)).toThrow(
      new OrganizerDatasetIntegrityError(
        'Account ACC-0024 does not reconcile: opening 1396.52 plus transactions 423.10 is not closing 1819.63',
      ),
    );
  });

  it('rejects a transaction of an unknown account', () => {
    const records = recordsWith({
      accounts: personaRecords.accounts.filter(
        (account) => account.accountId !== 'ACC-0143',
      ),
    });

    expect(() => OrganizerDataset.fromRecords(records)).toThrow(
      new OrganizerDatasetIntegrityError(
        'Transaction TX-0002324 belongs to unknown account ACC-0143',
      ),
    );
  });

  it('rejects a transaction in another currency than its account', () => {
    const records = recordsWith({
      transactions: personaRecords.transactions.map((transaction) =>
        transaction.transactionId === 'TX-0000216'
          ? { ...transaction, currency: 'GEL' }
          : transaction,
      ),
    });

    expect(() => OrganizerDataset.fromRecords(records)).toThrow(
      new OrganizerDatasetIntegrityError(
        'Transaction TX-0000216 is in GEL but account ACC-0179 is in USD',
      ),
    );
  });

  it('rejects a dataset without transactions', () => {
    const records = recordsWith({ accounts: [], transactions: [] });

    expect(() => OrganizerDataset.fromRecords(records)).toThrow(
      OrganizerDatasetIntegrityError,
    );
  });
});
