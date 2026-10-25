import {
  createFakeAisProvider,
  createFakeAisProviderResolver,
  type FakeAisProvider,
  type FakeAisProviderResolver,
} from '../../../test/support/fake-ais-provider.js';
import type { AisReadContext } from '../providers/ais-data-provider.js';
import type { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import type { TransactionListQueryDto } from './dto/transaction-list-query.dto.js';
import type { TransactionsResponseDto } from './dto/transactions-response.dto.js';
import { TransactionsService } from './transactions.service.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const context: AisReadContext = {
  consentId: CONSENT_ID,
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
};
const personaReport: TransactionsResponseDto = {
  account: { iban: 'GE38XX0000000000000024', currency: 'GEL' },
  transactions: {
    booked: [
      {
        transactionId: 'TX-0000117',
        transactionAmount: { currency: 'GEL', amount: '159.92' },
      },
    ],
    _links: { account: { href: '/v1/accounts/ACC-0024' } },
  },
};

describe('TransactionsService', () => {
  let provider: FakeAisProvider;
  let providerResolver: FakeAisProviderResolver;
  let transactionsService: TransactionsService;

  beforeEach(() => {
    provider = createFakeAisProvider('organizer-dataset');
    provider.readTransactions.mockResolvedValue(personaReport);
    providerResolver = createFakeAisProviderResolver(provider);
    transactionsService = new TransactionsService(
      providerResolver as unknown as AisProviderResolver,
    );
  });

  it('labels the report of the provider resolved for the consent with its data source', async () => {
    const report = await transactionsService.readTransactions(
      context,
      'ACC-0024',
      {},
    );

    expect(providerResolver.resolve).toHaveBeenCalledWith(CONSENT_ID);
    expect(report).toEqual({
      dataSource: 'organizer-dataset',
      body: personaReport,
    });
  });

  it.each<[string, TransactionListQueryDto, object]>([
    ['no query', {}, { bookingStatus: 'booked' }],
    [
      'a date range',
      { dateFrom: '2026-04-20', dateTo: '2026-10-19' },
      { dateFrom: '2026-04-20', dateTo: '2026-10-19', bookingStatus: 'booked' },
    ],
    [
      'a single day',
      { dateFrom: '2026-05-08', dateTo: '2026-05-08' },
      { dateFrom: '2026-05-08', dateTo: '2026-05-08', bookingStatus: 'booked' },
    ],
    [
      'bookingStatus both',
      { bookingStatus: 'both' },
      { bookingStatus: 'both' },
    ],
    [
      'bookingStatus pending',
      { bookingStatus: 'pending' },
      { bookingStatus: 'pending' },
    ],
  ])(
    'asks the provider for %s with booked as default booking status',
    async (_case, query, expectedQuery) => {
      await transactionsService.readTransactions(context, 'ACC-0024', query);

      expect(provider.readTransactions).toHaveBeenCalledWith(
        context,
        'ACC-0024',
        expectedQuery,
      );
    },
  );

  it('rejects dateFrom after dateTo with 400 FORMAT_ERROR without reading transactions', async () => {
    const reading = transactionsService.readTransactions(context, 'ACC-0024', {
      dateFrom: '2026-05-09',
      dateTo: '2026-05-08',
    });

    await expect(reading).rejects.toMatchObject({
      problem: {
        status: 400,
        code: 'FORMAT_ERROR',
        detail: 'dateFrom must not be after dateTo',
      },
    });
    expect(provider.readTransactions).not.toHaveBeenCalled();
  });
});
