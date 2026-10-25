import {
  createFakeAisProvider,
  createFakeAisProviderResolver,
  type FakeAisProvider,
  type FakeAisProviderResolver,
} from '../../../test/support/fake-ais-provider.js';
import type { AisReadContext } from '../providers/ais-data-provider.js';
import type { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import { BalancesService } from './balances.service.js';
import type { ReadAccountBalanceResponseDto } from './dto/read-account-balance-response.dto.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const context: AisReadContext = {
  consentId: CONSENT_ID,
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
};
const sandboxBalances: ReadAccountBalanceResponseDto = {
  account: { iban: 'GE11TB1000000000000010', currency: 'GEL' },
  balances: [
    {
      balanceType: 'interimBooked',
      balanceAmount: { currency: 'GEL', amount: '3247.50' },
    },
  ],
};

describe('BalancesService', () => {
  let provider: FakeAisProvider;
  let providerResolver: FakeAisProviderResolver;
  let balancesService: BalancesService;

  beforeEach(() => {
    provider = createFakeAisProvider('tbc-sandbox');
    provider.readBalances.mockResolvedValue(sandboxBalances);
    providerResolver = createFakeAisProviderResolver(provider);
    balancesService = new BalancesService(
      providerResolver as unknown as AisProviderResolver,
    );
  });

  it('reads the balances through the provider resolved for the consent', async () => {
    await balancesService.readBalances(context, 'acc-gel-001');

    expect(providerResolver.resolve).toHaveBeenCalledWith(CONSENT_ID);
    expect(provider.readBalances).toHaveBeenCalledWith(context, 'acc-gel-001');
  });

  it('labels the balances with the data source of that provider', async () => {
    const balances = await balancesService.readBalances(context, 'acc-gel-001');

    expect(balances).toEqual({
      dataSource: 'tbc-sandbox',
      body: sandboxBalances,
    });
  });
});
