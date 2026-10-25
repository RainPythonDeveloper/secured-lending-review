import {
  createFakeAisProvider,
  createFakeAisProviderResolver,
  type FakeAisProvider,
  type FakeAisProviderResolver,
} from '../../../test/support/fake-ais-provider.js';
import type { AisReadContext } from '../providers/ais-data-provider.js';
import type { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import { AccountsService } from './accounts.service.js';
import type { AccountDetailsDto } from './dto/account-details.dto.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const context: AisReadContext = {
  consentId: CONSENT_ID,
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
};
const personaAccount: AccountDetailsDto = {
  resourceId: 'ACC-0024',
  iban: 'GE38XX0000000000000024',
  currency: 'GEL',
};

describe('AccountsService', () => {
  let provider: FakeAisProvider;
  let providerResolver: FakeAisProviderResolver;
  let accountsService: AccountsService;

  beforeEach(() => {
    provider = createFakeAisProvider('organizer-dataset');
    providerResolver = createFakeAisProviderResolver(provider);
    accountsService = new AccountsService(
      providerResolver as unknown as AisProviderResolver,
    );
  });

  describe('listAccounts', () => {
    it('lists the accounts through the provider resolved for the consent', async () => {
      provider.listAccounts.mockResolvedValue({ accounts: [personaAccount] });

      await accountsService.listAccounts(context, true);

      expect(providerResolver.resolve).toHaveBeenCalledWith(CONSENT_ID);
      expect(provider.listAccounts).toHaveBeenCalledWith(context, true);
    });

    it('labels the accounts with the data source of that provider', async () => {
      provider.listAccounts.mockResolvedValue({ accounts: [personaAccount] });

      const accountList = await accountsService.listAccounts(context, false);

      expect(accountList).toEqual({
        dataSource: 'organizer-dataset',
        body: { accounts: [personaAccount] },
      });
    });
  });

  describe('readAccountDetails', () => {
    it('reads the account through the resolved provider and labels it with its data source', async () => {
      provider.readAccountDetails.mockResolvedValue({
        account: personaAccount,
      });

      const accountDetails = await accountsService.readAccountDetails(
        context,
        'ACC-0024',
        true,
      );

      expect(provider.readAccountDetails).toHaveBeenCalledWith(
        context,
        'ACC-0024',
        true,
      );
      expect(accountDetails).toEqual({
        dataSource: 'organizer-dataset',
        body: { account: personaAccount },
      });
    });
  });
});
