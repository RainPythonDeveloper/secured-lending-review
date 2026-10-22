import request from 'supertest';
import { authoriseConsent } from './support/authorise-consent.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';
import { upstreamConsentDetails } from './support/upstream-responses.js';

const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';
const AMOUNT_WITH_TWO_DECIMALS = /^-?\d+\.\d{2}$/;

interface TransactionBody {
  readonly transactionId?: string;
  readonly transactionAmount: { readonly amount: string };
  readonly debtorName?: string;
  readonly creditorName?: string;
}

describe('AIS transactions', () => {
  let testApp: TestApp;

  beforeEach(async () => {
    testApp = await createTestApp();
  });

  afterEach(async () => {
    await testApp.app.close();
  });

  function readTransactions(
    accountId: string,
    consentId: string,
    query: Record<string, string> = {},
  ) {
    return request(testApp.app.getHttpServer())
      .get(`/v1/accounts/${accountId}/transactions`)
      .query(query)
      .set({ 'Consent-ID': consentId });
  }

  async function authorisePersonaConsent(psuId = 'CUS-024'): Promise<string> {
    testApp.fakeTbcClient.getConsent.mockResolvedValue(
      upstreamConsentDetails(),
    );
    return authoriseConsent(testApp.app, testApp.fakeTbcClient, { psuId });
  }

  describe('sandbox consents', () => {
    it('answers booked and pending bank entries with the gateway account link', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      const response = await readTransactions('acc-gel-001', consentId, {
        bookingStatus: 'both',
      });

      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('tbc-sandbox');
      expect(response.body.transactions.booked).toHaveLength(5);
      expect(response.body.transactions.pending).toEqual([
        {
          transactionAmount: { currency: 'GEL', amount: '-22.50' },
          valueDate: '2026-10-20',
          remittanceInformationUnstructured: 'Pending synthetic purchase',
        },
      ]);
      expect(response.body.transactions._links).toEqual({
        account: { href: '/v1/accounts/acc-gel-001' },
      });
    });

    it('asks the bank for booked entries when no booking status is given', async () => {
      const consentId = await authoriseConsent(
        testApp.app,
        testApp.fakeTbcClient,
      );

      await readTransactions('acc-gel-001', consentId, {
        dateFrom: '2026-10-01',
        dateTo: '2026-10-05',
      });

      expect(testApp.fakeTbcClient.readTransactions).toHaveBeenCalledWith(
        { consentId, accessToken: 'access_fixture-not-a-real-token' },
        'acc-gel-001',
        {
          dateFrom: '2026-10-01',
          dateTo: '2026-10-05',
          bookingStatus: 'booked',
        },
        expect.objectContaining({ gatewayRequestId: expect.any(String) }),
      );
    });
  });

  describe('query validation', () => {
    it.each([
      ['bookingStatus all', { bookingStatus: 'all' }, 'bookingStatus must be'],
      [
        'dateFrom after dateTo',
        { dateFrom: '2026-05-09', dateTo: '2026-05-08' },
        'dateFrom must not be after dateTo',
      ],
      [
        'a dateFrom that is not an ISO date',
        { dateFrom: '09.05.2026' },
        'dateFrom must match',
      ],
      [
        'an unknown query parameter',
        { page: '1' },
        'property page should not exist',
      ],
    ])(
      'rejects %s with 400 FORMAT_ERROR without reading transactions',
      async (_case, query, expectedDetail) => {
        const consentId = await authoriseConsent(
          testApp.app,
          testApp.fakeTbcClient,
        );

        const response = await readTransactions(
          'acc-gel-001',
          consentId,
          query,
        );

        expect(response.status).toBe(400);
        expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
        expect(response.body.code).toBe('FORMAT_ERROR');
        expect(response.body.detail).toContain(expectedDetail);
        expect(testApp.fakeTbcClient.readTransactions).not.toHaveBeenCalled();
      },
    );
  });

  describe('persona consents', () => {
    it('answers the booked persona transactions with signed string amounts', async () => {
      const consentId = await authorisePersonaConsent();

      const response = await readTransactions('ACC-0024', consentId);

      const booked: TransactionBody[] = response.body.transactions.booked;
      expect(response.status).toBe(200);
      expect(response.headers['x-data-source']).toBe('organizer-dataset');
      expect(
        booked.map((transaction) => transaction.transactionAmount.amount),
      ).toEqual(['159.92', '277.98', '-14.80']);
      expect(
        booked.every((transaction) =>
          AMOUNT_WITH_TWO_DECIMALS.test(transaction.transactionAmount.amount),
        ),
      ).toBe(true);
      expect(response.body.transactions).not.toHaveProperty('pending');
    });

    it('names the payer of credits and the payee of debits', async () => {
      const consentId = await authorisePersonaConsent();

      const response = await readTransactions('ACC-0024', consentId);

      const booked: TransactionBody[] = response.body.transactions.booked;
      expect(
        booked.map(({ debtorName, creditorName }) => ({
          debtorName,
          creditorName,
        })),
      ).toEqual([
        { debtorName: 'Customer settlement 3 (synthetic)' },
        { debtorName: 'Customer settlement 4 (synthetic)' },
        { creditorName: 'Levan Gelashvili' },
      ]);
    });

    it('includes the transactions booked on dateFrom and on dateTo', async () => {
      const consentId = await authorisePersonaConsent();

      const response = await readTransactions('ACC-0024', consentId, {
        dateFrom: '2026-04-24',
        dateTo: '2026-05-08',
      });

      const booked: TransactionBody[] = response.body.transactions.booked;
      expect(booked.map((transaction) => transaction.transactionId)).toEqual([
        'TX-0000465',
        'TX-0002323',
      ]);
    });

    it('answers bookingStatus pending with an empty pending list only', async () => {
      const consentId = await authorisePersonaConsent();

      const response = await readTransactions('ACC-0024', consentId, {
        bookingStatus: 'pending',
      });

      expect(response.status).toBe(200);
      expect(response.body.transactions).toEqual({
        pending: [],
        _links: { account: { href: '/v1/accounts/ACC-0024' } },
      });
    });

    it('describes the currency conversion of persona CUS-011', async () => {
      const consentId = await authorisePersonaConsent('CUS-011');

      const response = await readTransactions('ACC-0179', consentId);

      expect(response.body.transactions.booked[1]).toMatchObject({
        transactionId: 'TX-0000217',
        transactionAmount: { currency: 'USD', amount: '-1163.30' },
        creditorAccount: { iban: 'GE98XX0000000000000011', currency: 'GEL' },
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

    it('answers 401 CONSENT_INVALID when the bank reports the consent as terminated', async () => {
      const consentId = await authorisePersonaConsent();
      testApp.fakeTbcClient.getConsent.mockResolvedValue(
        upstreamConsentDetails({ consentStatus: 'terminatedByTpp' }),
      );

      const response = await readTransactions('ACC-0024', consentId);

      expect(response.status).toBe(401);
      expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
      expect(response.body).toMatchObject({
        code: 'CONSENT_INVALID',
        detail: 'Consent is terminatedByTpp',
      });
    });

    it('answers 403 CONSENT_INVALID when the consent does not grant transactions', async () => {
      const consentId = await authorisePersonaConsent();
      testApp.fakeTbcClient.getConsent.mockResolvedValue(
        upstreamConsentDetails({
          access: { availableAccountsWithBalance: 'allAccounts' },
        }),
      );

      const response = await readTransactions('ACC-0024', consentId);

      expect(response.status).toBe(403);
      expect(response.body).toMatchObject({
        code: 'CONSENT_INVALID',
        detail: 'Consent does not allow transactions for this account',
      });
    });
  });
});
