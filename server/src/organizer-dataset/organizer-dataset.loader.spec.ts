import { fileURLToPath } from 'node:url';
import { Logger } from '@nestjs/common';
import type { MockInstance } from 'vitest';
import type { OrganizerDataset } from './organizer-dataset.js';
import { loadOrganizerDataset } from './organizer-dataset.loader.js';

const WORKBOOK_PATH = fileURLToPath(
  new URL(
    '../../../data/open-banking-synthetic-100-customers.xlsx',
    import.meta.url,
  ),
);

describe('loadOrganizerDataset with the organizer workbook', () => {
  let dataset: OrganizerDataset;
  let logSpy: MockInstance<Logger['log']>;

  beforeAll(async () => {
    logSpy = vi
      .spyOn(Logger.prototype, 'log')
      .mockImplementation(() => undefined);
    dataset = await loadOrganizerDataset(WORKBOOK_PATH);
  });

  afterAll(() => {
    logSpy.mockRestore();
  });

  it('loads every customer, account and transaction', () => {
    expect(dataset.counts).toEqual({
      customers: 100,
      accounts: 226,
      transactions: 23869,
    });
  });

  it('logs the record counts', () => {
    expect(logSpy).toHaveBeenCalledWith(
      'Organizer dataset loaded: 100 customers, 226 accounts, 23869 transactions',
    );
  });

  it('reads amounts as exact integer minor units', () => {
    const transaction = dataset
      .listTransactions('ACC-0001')
      .find((candidate) => candidate.transactionId === 'TX-0000202');

    expect(transaction?.amountMinorUnits).toBe(-3986);
  });

  it('exposes ACC-0024 as the only payment account of CUS-024', () => {
    const accounts = dataset.listPaymentAccounts('CUS-024');

    expect(accounts.map((account) => account.accountId)).toEqual(['ACC-0024']);
  });

  it('holds the 284 transactions of ACC-0024', () => {
    expect(dataset.listTransactions('ACC-0024')).toHaveLength(284);
  });

  it('reads booking dates as ISO dates up to the end of the coverage period', () => {
    expect(dataset.coverageEndDate).toBe('2026-10-19');
  });
});
