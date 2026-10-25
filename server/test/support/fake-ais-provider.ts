import type { Mock } from 'vitest';
import type { AisDataProvider } from '../../src/ais/providers/ais-data-provider.js';
import type { AisProviderResolver } from '../../src/ais/providers/ais-provider-resolver.js';
import type { DataSource } from '../../src/common/data-source/data-source.js';

type AisReadMethodName = Exclude<keyof AisDataProvider, 'dataSource'>;

export type FakeAisProvider = { readonly dataSource: DataSource } & {
  [MethodName in AisReadMethodName]: Mock<AisDataProvider[MethodName]>;
};

export interface FakeAisProviderResolver {
  readonly resolve: Mock<AisProviderResolver['resolve']>;
}

export function createFakeAisProvider(dataSource: DataSource): FakeAisProvider {
  return {
    dataSource,
    listAccounts: vi.fn<AisDataProvider['listAccounts']>(),
    readAccountDetails: vi.fn<AisDataProvider['readAccountDetails']>(),
    readBalances: vi.fn<AisDataProvider['readBalances']>(),
    readTransactions: vi.fn<AisDataProvider['readTransactions']>(),
  };
}

export function createFakeAisProviderResolver(
  provider: AisDataProvider,
): FakeAisProviderResolver {
  return {
    resolve: vi.fn<AisProviderResolver['resolve']>().mockReturnValue(provider),
  };
}
