import { loadSandboxFixture } from '../../../../test/fixtures/load-fixture.js';
import {
  createFakeTbcClient,
  type FakeTbcClient,
} from '../../../../test/support/fake-tbc-client.js';
import {
  STORED_ACCESS_TOKEN,
  createOAuthServiceWithTokens,
} from '../../../../test/support/oauth-service-with-tokens.js';
import {
  ProblemDetailsException,
  createProblem,
} from '../../../common/problem-details/problem-details.js';
import type { TbcClientService } from '../../../tbc-client/tbc-client.service.js';
import type { AisReadContext } from '../ais-data-provider.js';
import { SandboxAisProvider } from './sandbox-ais-provider.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const UNAUTHORISED_CONSENT_ID = '7c6b5a4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d';
const context: AisReadContext = {
  consentId: CONSENT_ID,
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
  psuIpAddress: '203.0.113.7',
};
const authorisation = {
  consentId: CONSENT_ID,
  accessToken: STORED_ACCESS_TOKEN,
};
const gatewayLinksOfGelAccount = {
  account: { href: '/v1/accounts/acc-gel-001' },
  balances: { href: '/v1/accounts/acc-gel-001/balances' },
  transactions: { href: '/v1/accounts/acc-gel-001/transactions' },
};

interface TransactionsFixture {
  readonly transactions: {
    readonly booked: unknown;
    readonly pending: unknown;
  };
}

describe('SandboxAisProvider', () => {
  let fakeTbcClient: FakeTbcClient;
  let provider: SandboxAisProvider;

  beforeEach(() => {
    fakeTbcClient = createFakeTbcClient();
    provider = new SandboxAisProvider(
      fakeTbcClient as unknown as TbcClientService,
      createOAuthServiceWithTokens(fakeTbcClient, [CONSENT_ID]),
    );
  });

  it('labels its data as TBC sandbox data', () => {
    expect(provider.dataSource).toBe('tbc-sandbox');
  });

  describe('listAccounts', () => {
    it('lists the accounts at the bank with the Bearer token stored for the consent', async () => {
      await provider.listAccounts(context, true);

      expect(fakeTbcClient.listAccounts).toHaveBeenCalledWith(
        authorisation,
        true,
        context,
      );
    });

    it('replaces the upstream account links with gateway links', async () => {
      const accountList = await provider.listAccounts(context, true);

      expect(accountList.accounts.map((account) => account._links)).toEqual([
        gatewayLinksOfGelAccount,
        {
          account: { href: '/v1/accounts/acc-usd-002' },
          balances: { href: '/v1/accounts/acc-usd-002/balances' },
          transactions: { href: '/v1/accounts/acc-usd-002/transactions' },
        },
      ]);
    });

    it('keeps the account fields and string balances of the bank', async () => {
      const accountList = await provider.listAccounts(context, true);

      expect(accountList.accounts[0]).toMatchObject({
        resourceId: 'acc-gel-001',
        iban: 'GE11TB1000000000000010',
        currency: 'GEL',
        displayName: 'ყოველდღიური ანგარიში',
        balances: [
          {
            balanceType: 'interimBooked',
            balanceAmount: { amount: '3247.50' },
          },
          {
            balanceType: 'interimAvailable',
            balanceAmount: { amount: '3225.00' },
          },
        ],
      });
    });

    it('rejects a numeric balance amount as an upstream contract violation', async () => {
      fakeTbcClient.listAccounts.mockResolvedValue({
        accounts: [
          {
            resourceId: 'acc-gel-001',
            currency: 'GEL',
            balances: [
              {
                balanceType: 'interimBooked',
                balanceAmount: { currency: 'GEL', amount: 3247.5 },
              },
            ],
          },
        ],
      });

      const listing = provider.listAccounts(context, true);

      await expect(listing).rejects.toMatchObject({
        problem: { status: 502, code: 'UPSTREAM_CONTRACT_VIOLATION' },
      });
    });

    it('refuses a consent without gateway tokens with 401 TOKEN_INVALID before calling the bank', async () => {
      const listing = provider.listAccounts(
        { ...context, consentId: UNAUTHORISED_CONSENT_ID },
        false,
      );

      await expect(listing).rejects.toMatchObject({
        problem: { status: 401, code: 'TOKEN_INVALID' },
      });
      expect(fakeTbcClient.listAccounts).not.toHaveBeenCalled();
    });

    it('propagates a bank problem unchanged', async () => {
      const tokenInvalid = new ProblemDetailsException(
        createProblem({
          status: 401,
          code: 'TOKEN_INVALID',
          detail: 'A valid mock bearer token is required',
        }),
      );
      fakeTbcClient.listAccounts.mockRejectedValue(tokenInvalid);

      const listing = provider.listAccounts(context, false);

      await expect(listing).rejects.toBe(tokenInvalid);
    });
  });

  describe('readAccountDetails', () => {
    it('reads the account at the bank and links it to gateway routes', async () => {
      const accountDetails = await provider.readAccountDetails(
        context,
        'acc-gel-001',
        false,
      );

      expect(fakeTbcClient.readAccountDetails).toHaveBeenCalledWith(
        authorisation,
        'acc-gel-001',
        false,
        context,
      );
      expect(accountDetails.account).toMatchObject({
        resourceId: 'acc-gel-001',
        ownerName: 'მოქი მოქიაშვილი',
        _links: gatewayLinksOfGelAccount,
      });
    });
  });

  describe('readBalances', () => {
    it('returns the balances of the bank', async () => {
      const balances = await provider.readBalances(context, 'acc-gel-001');

      expect(fakeTbcClient.readBalances).toHaveBeenCalledWith(
        authorisation,
        'acc-gel-001',
        context,
      );
      expect(balances).toEqual(
        loadSandboxFixture('balances.acc-gel-001.200.json'),
      );
    });
  });

  describe('readTransactions', () => {
    it('passes the booking status and date range to the bank', async () => {
      const query = {
        dateFrom: '2026-10-01',
        dateTo: '2026-10-05',
        bookingStatus: 'both',
      } as const;

      await provider.readTransactions(context, 'acc-gel-001', query);

      expect(fakeTbcClient.readTransactions).toHaveBeenCalledWith(
        authorisation,
        'acc-gel-001',
        query,
        context,
      );
    });

    it('keeps booked and pending entries and links the report to the gateway account route', async () => {
      const fixture = loadSandboxFixture(
        'transactions.acc-gel-001.both.200.json',
      ) as TransactionsFixture;

      const report = await provider.readTransactions(context, 'acc-gel-001', {
        bookingStatus: 'both',
      });

      expect(report.transactions).toEqual({
        booked: fixture.transactions.booked,
        pending: fixture.transactions.pending,
        _links: { account: { href: '/v1/accounts/acc-gel-001' } },
      });
    });

    it('answers booked entries only when the bank sends no pending list', async () => {
      fakeTbcClient.readTransactions.mockResolvedValue(
        loadSandboxFixture('transactions.acc-gel-001.booked.200.json'),
      );

      const report = await provider.readTransactions(context, 'acc-gel-001', {
        bookingStatus: 'booked',
      });

      expect(report.transactions.booked).toHaveLength(5);
      expect(report.transactions.pending).toBeUndefined();
    });
  });
});
