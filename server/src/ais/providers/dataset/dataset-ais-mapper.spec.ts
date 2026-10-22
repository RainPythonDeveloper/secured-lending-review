import { personaRecords } from '../../../../test/fixtures/organizer-dataset/persona-records.js';
import type {
  AccountRecord,
  CustomerRecord,
  TransactionRecord,
} from '../../../organizer-dataset/dataset-records.js';
import {
  mapAccount,
  mapAccountReference,
  mapBalances,
  mapTransaction,
} from './dataset-ais-mapper.js';

const COVERAGE_END_DATE = '2026-10-19';

function findCustomer(customerId: string): CustomerRecord {
  const customer = personaRecords.customers.find(
    (record) => record.customerId === customerId,
  );
  if (customer === undefined) {
    throw new Error(`Fixture customer ${customerId} is missing`);
  }
  return customer;
}

function findAccount(accountId: string): AccountRecord {
  const account = personaRecords.accounts.find(
    (record) => record.accountId === accountId,
  );
  if (account === undefined) {
    throw new Error(`Fixture account ${accountId} is missing`);
  }
  return account;
}

function findTransaction(transactionId: string): TransactionRecord {
  const transaction = personaRecords.transactions.find(
    (record) => record.transactionId === transactionId,
  );
  if (transaction === undefined) {
    throw new Error(`Fixture transaction ${transactionId} is missing`);
  }
  return transaction;
}

describe('mapAccount', () => {
  it('maps a current account to AIS account details with a synthetic IBAN and gateway links', () => {
    const account = mapAccount(
      findAccount('ACC-0024'),
      findCustomer('CUS-024'),
    );

    expect(account).toEqual({
      resourceId: 'ACC-0024',
      iban: 'GE38XX0000000000000024',
      currency: 'GEL',
      name: 'Current account',
      ownerName: 'Levan Gelashvili',
      cashAccountType: 'CACC',
      status: 'enabled',
      usage: 'PRIV',
      _links: {
        account: { href: '/v1/accounts/ACC-0024' },
        balances: { href: '/v1/accounts/ACC-0024/balances' },
        transactions: { href: '/v1/accounts/ACC-0024/transactions' },
      },
    });
  });

  it('maps a closed dataset account to status deleted', () => {
    const closedAccount: AccountRecord = {
      ...findAccount('ACC-0024'),
      status: 'closed',
    };

    const account = mapAccount(closedAccount, findCustomer('CUS-024'));

    expect(account.status).toBe('deleted');
  });

  it('attaches the given balances', () => {
    const accountRecord = findAccount('ACC-0179');
    const balances = mapBalances(accountRecord, COVERAGE_END_DATE);

    const account = mapAccount(
      accountRecord,
      findCustomer('CUS-011'),
      balances,
    );

    expect(account.balances).toBe(balances);
  });
});

describe('mapAccountReference', () => {
  it('references the account by synthetic IBAN and currency', () => {
    const reference = mapAccountReference(findAccount('ACC-0179'));

    expect(reference).toEqual({
      iban: 'GE24XX0000000000000179',
      currency: 'USD',
    });
  });
});

describe('mapBalances', () => {
  it('reports the closing balance as booked and available at the coverage end date', () => {
    const balances = mapBalances(findAccount('ACC-0024'), COVERAGE_END_DATE);

    expect(balances).toEqual([
      {
        balanceType: 'interimBooked',
        balanceAmount: { currency: 'GEL', amount: '1819.62' },
        creditLimitIncluded: false,
        referenceDate: COVERAGE_END_DATE,
      },
      {
        balanceType: 'interimAvailable',
        balanceAmount: { currency: 'GEL', amount: '1819.62' },
        creditLimitIncluded: false,
        referenceDate: COVERAGE_END_DATE,
      },
    ]);
  });
});

describe('mapTransaction', () => {
  it('maps a cash business income credit with the payer as debtorName', () => {
    const transaction = mapTransaction(findTransaction('TX-0000117'));

    expect(transaction).toEqual({
      transactionId: 'TX-0000117',
      entryReference: '117',
      bookingDate: '2026-04-21',
      valueDate: '2026-04-21',
      transactionAmount: { currency: 'GEL', amount: '159.92' },
      debtorName: 'Customer settlement 3 (synthetic)',
      remittanceInformationUnstructured: 'Small business receipts',
      additionalInformation: 'cash',
      proprietaryBankTransactionCode: 'business_income',
      balanceAfterTransaction: {
        balanceType: 'interimBooked',
        balanceAmount: { currency: 'GEL', amount: '1479.78' },
      },
    });
  });

  it('maps an own transfer debit with the payee and the savings account as creditor', () => {
    const transaction = mapTransaction(
      findTransaction('TX-0002323'),
      findAccount('ACC-0143'),
    );

    expect(transaction).toMatchObject({
      transactionAmount: { currency: 'GEL', amount: '-14.80' },
      creditorName: 'Levan Gelashvili',
      creditorAccount: { iban: 'GE26XX0000000000000143', currency: 'GEL' },
      endToEndId: 'TRF-00112',
    });
    expect(transaction).not.toHaveProperty('debtorName');
  });

  it('describes the USD to GEL conversion on the debit leg', () => {
    const transaction = mapTransaction(
      findTransaction('TX-0000217'),
      findAccount('ACC-0011'),
    );

    expect(transaction.currencyExchange).toEqual([
      {
        sourceCurrency: 'USD',
        exchangeRate: '2.7101',
        unitCurrency: 'USD',
        targetCurrency: 'GEL',
        quotationDate: '2026-04-22',
      },
    ]);
  });

  it('describes the same USD to GEL conversion on the credit leg', () => {
    const transaction = mapTransaction(
      findTransaction('TX-0000218'),
      findAccount('ACC-0179'),
    );

    expect(transaction).toMatchObject({
      transactionAmount: { currency: 'GEL', amount: '3152.66' },
      debtorName: 'Synthetic FX desk',
      debtorAccount: { iban: 'GE24XX0000000000000179', currency: 'USD' },
      currencyExchange: [
        {
          sourceCurrency: 'USD',
          exchangeRate: '2.7101',
          unitCurrency: 'USD',
          targetCurrency: 'GEL',
          quotationDate: '2026-04-22',
        },
      ],
    });
  });

  it('leaves out the exchange rate of a transaction without fx_rate', () => {
    const transaction = mapTransaction(
      findTransaction('TX-0002323'),
      findAccount('ACC-0143'),
    );

    expect(transaction.currencyExchange).toBeUndefined();
  });
});
