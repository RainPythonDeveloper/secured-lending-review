import { loadSandboxFixture } from '../../../../test/fixtures/load-fixture.js';
import { personaRecords } from '../../../../test/fixtures/organizer-dataset/persona-records.js';
import {
  createFakeTbcClient,
  type FakeTbcClient,
} from '../../../../test/support/fake-tbc-client.js';
import { createOAuthServiceWithTokens } from '../../../../test/support/oauth-service-with-tokens.js';
import { OrganizerDataset } from '../../../organizer-dataset/organizer-dataset.js';
import type { TbcClientService } from '../../../tbc-client/tbc-client.service.js';
import type { BookingStatus } from '../../shared/ais-formats.js';
import type { AisReadContext } from '../ais-data-provider.js';
import { PersonaBindingStore } from '../persona-binding.store.js';
import { DatasetAisProvider } from './dataset-ais-provider.js';

const LEVAN_CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const ELENE_CONSENT_ID = '8d7c6b5a-4f3e-4d2c-9b1a-0f9e8d7c6b5a';
const UNAUTHORISED_CONSENT_ID = '7c6b5a4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d';
const UNBOUND_CONSENT_ID = '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d';
const PERSONA_COVERAGE_END_DATE = '2026-05-08';
const bankOfferedAccess = { accounts: [], balances: [], transactions: [] };
const levanContext: AisReadContext = {
  consentId: LEVAN_CONSENT_ID,
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
  psuIpAddress: '203.0.113.7',
};

function upstreamConsent(changes: Record<string, unknown>): unknown {
  return {
    ...(loadSandboxFixture('consent-details.200.json') as object),
    ...changes,
  };
}

describe('DatasetAisProvider', () => {
  let fakeTbcClient: FakeTbcClient;
  let bindings: PersonaBindingStore;
  let provider: DatasetAisProvider;

  beforeEach(() => {
    fakeTbcClient = createFakeTbcClient();
    fakeTbcClient.getConsent.mockResolvedValue(
      upstreamConsent({ access: bankOfferedAccess }),
    );
    bindings = new PersonaBindingStore();
    bindings.bind(LEVAN_CONSENT_ID, 'CUS-024');
    bindings.bind(ELENE_CONSENT_ID, 'CUS-011');
    bindings.bind(UNAUTHORISED_CONSENT_ID, 'CUS-024');
    provider = new DatasetAisProvider(
      fakeTbcClient as unknown as TbcClientService,
      createOAuthServiceWithTokens(fakeTbcClient, [
        LEVAN_CONSENT_ID,
        ELENE_CONSENT_ID,
        UNBOUND_CONSENT_ID,
      ]),
      OrganizerDataset.fromRecords(personaRecords),
      bindings,
    );
  });

  function grantAccess(access: Record<string, unknown>): void {
    fakeTbcClient.getConsent.mockResolvedValue(upstreamConsent({ access }));
  }

  it('labels its data as organizer dataset data', () => {
    expect(provider.dataSource).toBe('organizer-dataset');
  });

  describe('consent checks', () => {
    it('reads the consent status and access from the bank on every request', async () => {
      await provider.listAccounts(levanContext, false);

      expect(fakeTbcClient.getConsent).toHaveBeenCalledWith(
        LEVAN_CONSENT_ID,
        levanContext,
      );
    });

    it('refuses a consent without gateway tokens with 401 TOKEN_INVALID before calling the bank', async () => {
      const listing = provider.listAccounts(
        { ...levanContext, consentId: UNAUTHORISED_CONSENT_ID },
        false,
      );

      await expect(listing).rejects.toMatchObject({
        problem: {
          status: 401,
          code: 'TOKEN_INVALID',
          detail: 'Consent has not been authorised through this gateway',
        },
      });
      expect(fakeTbcClient.getConsent).not.toHaveBeenCalled();
    });

    it('refuses a consent the bank no longer reports as valid with 401 CONSENT_INVALID', async () => {
      fakeTbcClient.getConsent.mockResolvedValue(
        upstreamConsent({ consentStatus: 'terminatedByTpp' }),
      );

      const listing = provider.listAccounts(levanContext, false);

      await expect(listing).rejects.toMatchObject({
        problem: {
          status: 401,
          code: 'CONSENT_INVALID',
          detail: 'Consent is terminatedByTpp',
        },
      });
    });

    it('fails loudly when it is asked to serve a consent without persona binding', async () => {
      const listing = provider.listAccounts(
        { ...levanContext, consentId: UNBOUND_CONSENT_ID },
        false,
      );

      await expect(listing).rejects.toThrow(
        'Consent is not bound to an organizer dataset customer',
      );
    });
  });

  describe('listAccounts', () => {
    it('lists the current accounts of the persona with synthetic IBANs', async () => {
      const accountList = await provider.listAccounts(levanContext, false);

      expect(accountList.accounts).toEqual([
        expect.objectContaining({
          resourceId: 'ACC-0024',
          iban: 'GE38XX0000000000000024',
          ownerName: 'Levan Gelashvili',
          cashAccountType: 'CACC',
        }),
      ]);
      expect(accountList.accounts[0]?.balances).toBeUndefined();
    });

    it('adds balances when asked and the consent grants them', async () => {
      const accountList = await provider.listAccounts(levanContext, true);

      expect(accountList.accounts[0]?.balances).toEqual([
        expect.objectContaining({
          balanceType: 'interimBooked',
          balanceAmount: { currency: 'GEL', amount: '1819.62' },
        }),
        expect.objectContaining({ balanceType: 'interimAvailable' }),
      ]);
    });

    it('leaves out balances the consent does not grant', async () => {
      grantAccess({ accounts: [] });

      const accountList = await provider.listAccounts(levanContext, true);

      expect(accountList.accounts[0]?.balances).toBeUndefined();
    });

    it('lists no account when the consent names other IBANs only', async () => {
      fakeTbcClient.getConsent.mockResolvedValue(
        loadSandboxFixture('consent-details.200.json'),
      );

      const accountList = await provider.listAccounts(levanContext, false);

      expect(accountList).toEqual({ accounts: [] });
    });
  });

  describe('readAccountDetails', () => {
    it('reads a current account of the persona', async () => {
      const accountDetails = await provider.readAccountDetails(
        levanContext,
        'ACC-0024',
        false,
      );

      expect(accountDetails.account).toMatchObject({
        resourceId: 'ACC-0024',
        _links: { account: { href: '/v1/accounts/ACC-0024' } },
      });
    });

    it.each([
      ['the persona savings account', 'ACC-0143'],
      ['an account of another persona', 'ACC-0011'],
      ['an account missing from the dataset', 'ACC-9999'],
    ])('answers 404 RESOURCE_UNKNOWN for %s', async (_case, accountId) => {
      const reading = provider.readAccountDetails(
        levanContext,
        accountId,
        false,
      );

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 404,
          code: 'RESOURCE_UNKNOWN',
          detail: 'Account resourceId not found',
        },
      });
    });

    it('answers 403 CONSENT_INVALID when the consent does not grant the account', async () => {
      grantAccess({ transactions: [] });

      const reading = provider.readAccountDetails(
        levanContext,
        'ACC-0024',
        false,
      );

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 403,
          code: 'CONSENT_INVALID',
          detail: 'Consent does not allow accounts for this account',
        },
      });
    });
  });

  describe('readBalances', () => {
    it('reports the closing balance at the end of the dataset coverage', async () => {
      const balances = await provider.readBalances(levanContext, 'ACC-0024');

      expect(balances).toEqual({
        account: { iban: 'GE38XX0000000000000024', currency: 'GEL' },
        balances: [
          {
            balanceType: 'interimBooked',
            balanceAmount: { currency: 'GEL', amount: '1819.62' },
            creditLimitIncluded: false,
            referenceDate: PERSONA_COVERAGE_END_DATE,
          },
          {
            balanceType: 'interimAvailable',
            balanceAmount: { currency: 'GEL', amount: '1819.62' },
            creditLimitIncluded: false,
            referenceDate: PERSONA_COVERAGE_END_DATE,
          },
        ],
      });
    });

    it('answers 403 CONSENT_INVALID for a consent to the account list only', async () => {
      grantAccess({ availableAccounts: 'allAccounts' });

      const reading = provider.readBalances(levanContext, 'ACC-0024');

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 403,
          code: 'CONSENT_INVALID',
          detail: 'Consent does not allow balances for this account',
        },
      });
    });
  });

  describe('readTransactions', () => {
    async function readTransactionIds(query: {
      dateFrom?: string;
      dateTo?: string;
    }): Promise<(string | undefined)[]> {
      const report = await provider.readTransactions(levanContext, 'ACC-0024', {
        ...query,
        bookingStatus: 'booked',
      });
      return (report.transactions.booked ?? []).map(
        (transaction) => transaction.transactionId,
      );
    }

    it('answers the booked transactions in booking order with the account reference', async () => {
      const report = await provider.readTransactions(levanContext, 'ACC-0024', {
        bookingStatus: 'booked',
      });

      expect(report.account).toEqual({
        iban: 'GE38XX0000000000000024',
        currency: 'GEL',
      });
      expect(
        report.transactions.booked?.map(
          (transaction) => transaction.transactionAmount.amount,
        ),
      ).toEqual(['159.92', '277.98', '-14.80']);
    });

    it.each([
      [
        'both bounds inclusive',
        { dateFrom: '2026-04-24', dateTo: '2026-05-08' },
        ['TX-0000465', 'TX-0002323'],
      ],
      [
        'a single day',
        { dateFrom: '2026-04-21', dateTo: '2026-04-21' },
        ['TX-0000117'],
      ],
      [
        'dateFrom only',
        { dateFrom: '2026-04-22' },
        ['TX-0000465', 'TX-0002323'],
      ],
      ['dateTo only', { dateTo: '2026-04-24' }, ['TX-0000117', 'TX-0000465']],
      ['a range without bookings', { dateFrom: '2026-06-01' }, []],
    ])(
      'filters booked transactions by booking date with %s',
      async (_case, query, expectedTransactionIds) => {
        const transactionIds = await readTransactionIds(query);

        expect(transactionIds).toEqual(expectedTransactionIds);
      },
    );

    it.each<[BookingStatus, string[]]>([
      ['booked', ['_links', 'booked']],
      ['pending', ['_links', 'pending']],
      ['both', ['_links', 'booked', 'pending']],
    ])(
      'answers bookingStatus %s with the report keys the sandbox uses',
      async (bookingStatus, expectedKeys) => {
        const report = await provider.readTransactions(
          levanContext,
          'ACC-0024',
          { bookingStatus },
        );

        expect(Object.keys(report.transactions).sort()).toEqual(expectedKeys);
      },
    );

    it('answers bookingStatus pending with an empty pending list', async () => {
      const report = await provider.readTransactions(levanContext, 'ACC-0024', {
        bookingStatus: 'pending',
      });

      expect(report.transactions).toEqual({
        pending: [],
        _links: { account: { href: '/v1/accounts/ACC-0024' } },
      });
    });

    it('names the counterparty account of a currency conversion', async () => {
      const report = await provider.readTransactions(
        { ...levanContext, consentId: ELENE_CONSENT_ID },
        'ACC-0179',
        { bookingStatus: 'booked' },
      );

      expect(report.transactions.booked?.[1]).toMatchObject({
        transactionId: 'TX-0000217',
        creditorAccount: { iban: 'GE98XX0000000000000011', currency: 'GEL' },
        currencyExchange: [{ sourceCurrency: 'USD', targetCurrency: 'GEL' }],
      });
    });

    it('answers 403 CONSENT_INVALID when the consent does not grant transactions', async () => {
      grantAccess({ availableAccountsWithBalance: 'allAccounts' });

      const reading = provider.readTransactions(levanContext, 'ACC-0024', {
        bookingStatus: 'booked',
      });

      await expect(reading).rejects.toMatchObject({
        problem: {
          status: 403,
          code: 'CONSENT_INVALID',
          detail: 'Consent does not allow transactions for this account',
        },
      });
    });
  });
});
