import type { Mock } from 'vitest';
import { TbcClientService } from '../../src/tbc-client/tbc-client.service.js';
import { loadSandboxFixture } from '../fixtures/load-fixture.js';

export type FakeTbcClient = {
  [MethodName in keyof TbcClientService]: Mock<TbcClientService[MethodName]>;
};

export function createFakeTbcClient(): FakeTbcClient {
  return {
    createConsent: vi
      .fn<TbcClientService['createConsent']>()
      .mockResolvedValue(loadSandboxFixture('create-consent.201.json')),
    getConsent: vi
      .fn<TbcClientService['getConsent']>()
      .mockResolvedValue(loadSandboxFixture('consent-details.200.json')),
    getConsentStatus: vi
      .fn<TbcClientService['getConsentStatus']>()
      .mockResolvedValue(loadSandboxFixture('consent-status.valid.200.json')),
    deleteConsent: vi
      .fn<TbcClientService['deleteConsent']>()
      .mockResolvedValue(undefined),
    exchangeAuthorisationCode: vi
      .fn<TbcClientService['exchangeAuthorisationCode']>()
      .mockResolvedValue(loadSandboxFixture('token.200.json')),
    refreshAccessToken: vi
      .fn<TbcClientService['refreshAccessToken']>()
      .mockResolvedValue(loadSandboxFixture('token.refreshed.200.json')),
    listAccounts: vi
      .fn<TbcClientService['listAccounts']>()
      .mockResolvedValue(loadSandboxFixture('accounts.with-balance.200.json')),
    readAccountDetails: vi
      .fn<TbcClientService['readAccountDetails']>()
      .mockResolvedValue(
        loadSandboxFixture('account-details.acc-gel-001.200.json'),
      ),
    readBalances: vi
      .fn<TbcClientService['readBalances']>()
      .mockResolvedValue(loadSandboxFixture('balances.acc-gel-001.200.json')),
    readTransactions: vi
      .fn<TbcClientService['readTransactions']>()
      .mockResolvedValue(
        loadSandboxFixture('transactions.acc-gel-001.both.200.json'),
      ),
  };
}
