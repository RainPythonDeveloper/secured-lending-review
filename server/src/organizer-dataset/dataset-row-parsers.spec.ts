import {
  parseAccountRow,
  parseCustomerRow,
  parseTransactionRow,
} from './dataset-row-parsers.js';
import { OrganizerDatasetFormatError } from './organizer-dataset-errors.js';
import type { DatasetCell, DatasetRow } from './xlsx-sheet-reader.js';

type Cells = Record<string, DatasetCell>;

const customerCells: Cells = {
  customer_id: 'CUS-024',
  full_name: 'Levan Gelashvili',
  age: '43',
  city: 'Zugdidi',
};

const accountCells: Cells = {
  account_id: 'ACC-0024',
  customer_id: 'CUS-024',
  account_type: 'current',
  currency: 'GEL',
  opened_date: '2023-06-24',
  closed_date: null,
  status: 'active',
  opening_balance: '1396.52',
  closing_balance: '8476.89',
};

const transactionCells: Cells = {
  transaction_id: 'TX-0000217',
  account_id: 'ACC-0179',
  customer_id: 'CUS-011',
  booking_date: '2026-04-22',
  posting_sequence: '217',
  currency: 'USD',
  category: 'fx_conversion',
  amount: '-1163.3',
  balance_after: '387.77',
  channel: 'fx',
  counterparty: 'Synthetic FX desk',
  description: 'Exchange USD to GEL',
  transfer_id: 'TRF-00008',
  related_account_id: 'ACC-0011',
  fx_rate: '2.7101',
  refund_of_id: null,
};

function datasetRow(sheetName: string, cells: Cells): DatasetRow {
  return { sheetName, rowNumber: 7, cells };
}

describe('parseCustomerRow', () => {
  it('parses the customer id and full name', () => {
    const customer = parseCustomerRow(datasetRow('Customers', customerCells));

    expect(customer).toEqual({
      customerId: 'CUS-024',
      fullName: 'Levan Gelashvili',
    });
  });

  it('rejects a customer without an id and names the sheet and row', () => {
    const row = datasetRow('Customers', {
      ...customerCells,
      customer_id: null,
    });

    expect(() => parseCustomerRow(row)).toThrow(
      new OrganizerDatasetFormatError(
        'Organizer dataset sheet Customers row 7: customer_id is required',
      ),
    );
  });
});

describe('parseAccountRow', () => {
  it('parses the account with balances in integer minor units', () => {
    const account = parseAccountRow(datasetRow('Accounts', accountCells));

    expect(account).toEqual({
      accountId: 'ACC-0024',
      customerId: 'CUS-024',
      accountType: 'current',
      currency: 'GEL',
      status: 'active',
      openingBalanceMinorUnits: 139652,
      closingBalanceMinorUnits: 847689,
    });
  });

  it('rejects an unknown account type', () => {
    const row = datasetRow('Accounts', {
      ...accountCells,
      account_type: 'credit_card',
    });

    expect(() => parseAccountRow(row)).toThrow(
      new OrganizerDatasetFormatError(
        'Organizer dataset sheet Accounts row 7: account_type "credit_card" is not one of current, savings, term_deposit',
      ),
    );
  });

  it('rejects an unknown account status', () => {
    const row = datasetRow('Accounts', { ...accountCells, status: 'frozen' });

    expect(() => parseAccountRow(row)).toThrow(OrganizerDatasetFormatError);
  });

  it('rejects a balance with more than two fraction digits', () => {
    const row = datasetRow('Accounts', {
      ...accountCells,
      closing_balance: '8476.891',
    });

    expect(() => parseAccountRow(row)).toThrow(
      new OrganizerDatasetFormatError(
        'Organizer dataset sheet Accounts row 7: closing_balance "8476.891" is not a decimal amount with at most 2 fraction digits',
      ),
    );
  });
});

describe('parseTransactionRow', () => {
  it('parses an FX transfer leg with its optional fields', () => {
    const transaction = parseTransactionRow(
      datasetRow('Transactions', transactionCells),
    );

    expect(transaction).toEqual({
      transactionId: 'TX-0000217',
      accountId: 'ACC-0179',
      bookingDate: '2026-04-22',
      postingSequence: 217,
      currency: 'USD',
      category: 'fx_conversion',
      amountMinorUnits: -116330,
      balanceAfterMinorUnits: 38777,
      channel: 'fx',
      counterparty: 'Synthetic FX desk',
      description: 'Exchange USD to GEL',
      transferId: 'TRF-00008',
      relatedAccountId: 'ACC-0011',
      fxRate: '2.7101',
    });
  });

  it('turns empty optional cells into null', () => {
    const row = datasetRow('Transactions', {
      ...transactionCells,
      transfer_id: null,
      related_account_id: null,
      fx_rate: null,
    });

    const transaction = parseTransactionRow(row);

    expect(transaction).toMatchObject({
      transferId: null,
      relatedAccountId: null,
      fxRate: null,
    });
  });

  it.each([
    [
      'a missing transaction id',
      { transaction_id: null },
      'transaction_id is required',
    ],
    [
      'a malformed transaction id',
      { transaction_id: 'TX 1' },
      'transaction_id "TX 1" is malformed',
    ],
    [
      'a booking date that is not an ISO date',
      { booking_date: '22.04.2026' },
      'booking_date "22.04.2026" is malformed',
    ],
    [
      'an amount in exponent notation',
      { amount: '1e3' },
      'amount "1e3" is not a decimal amount with at most 2 fraction digits',
    ],
    [
      'a fractional posting sequence',
      { posting_sequence: '217.5' },
      'posting_sequence "217.5" is malformed',
    ],
    [
      'a lower-case currency',
      { currency: 'usd' },
      'currency "usd" is malformed',
    ],
    [
      'a malformed related account',
      { related_account_id: 'CUS-011' },
      'related_account_id "CUS-011" is malformed',
    ],
    [
      'a missing counterparty',
      { counterparty: '' },
      'counterparty is required',
    ],
  ])('rejects a transaction with %s', (_case, overrides, expectedIssue) => {
    const row = datasetRow('Transactions', {
      ...transactionCells,
      ...overrides,
    });

    expect(() => parseTransactionRow(row)).toThrow(
      new OrganizerDatasetFormatError(
        `Organizer dataset sheet Transactions row 7: ${expectedIssue}`,
      ),
    );
  });
});
