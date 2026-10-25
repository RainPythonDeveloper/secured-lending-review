import type { AccountAccessDto } from '../../shared/dto/account-access.dto.js';
import { isServiceGranted } from './consent-access-policy.js';

const GEL_IBAN = 'GE38XX0000000000000024';
const USD_IBAN = 'GE24XX0000000000000179';

interface GrantedServices {
  readonly accounts: boolean;
  readonly balances: boolean;
  readonly transactions: boolean;
}

function readGrantedServices(
  access: AccountAccessDto,
  iban: string,
): GrantedServices {
  return {
    accounts: isServiceGranted(access, 'accounts', iban),
    balances: isServiceGranted(access, 'balances', iban),
    transactions: isServiceGranted(access, 'transactions', iban),
  };
}

const dedicatedGelAccess: AccountAccessDto = {
  accounts: [{ iban: GEL_IBAN }],
  balances: [{ iban: GEL_IBAN, currency: 'GEL' }],
  transactions: [{ iban: GEL_IBAN }],
};

describe('isServiceGranted', () => {
  it.each<[string, AccountAccessDto, string, GrantedServices]>([
    [
      'a dedicated GEL-only consent for the GEL account',
      dedicatedGelAccess,
      GEL_IBAN,
      { accounts: true, balances: true, transactions: true },
    ],
    [
      'a dedicated GEL-only consent for another account',
      dedicatedGelAccess,
      USD_IBAN,
      { accounts: false, balances: false, transactions: false },
    ],
    [
      'empty arrays for every service',
      { accounts: [], balances: [], transactions: [] },
      USD_IBAN,
      { accounts: true, balances: true, transactions: true },
    ],
    [
      'a mixed consent for an account outside its accounts list',
      { accounts: [{ iban: GEL_IBAN }], balances: [], transactions: [] },
      USD_IBAN,
      { accounts: false, balances: true, transactions: true },
    ],
    [
      'an accounts-only consent',
      { accounts: [] },
      GEL_IBAN,
      { accounts: true, balances: false, transactions: false },
    ],
    [
      'a transactions-only consent',
      { transactions: [] },
      GEL_IBAN,
      { accounts: false, balances: false, transactions: true },
    ],
    [
      'availableAccounts',
      { availableAccounts: 'allAccounts' },
      GEL_IBAN,
      { accounts: true, balances: false, transactions: false },
    ],
    [
      'availableAccountsWithBalance',
      { availableAccountsWithBalance: 'allAccountsWithOwnerName' },
      GEL_IBAN,
      { accounts: true, balances: true, transactions: false },
    ],
    [
      'availableAccounts next to service lists',
      { availableAccounts: 'allAccounts', transactions: [] },
      GEL_IBAN,
      { accounts: true, balances: false, transactions: false },
    ],
    [
      'no access at all',
      {},
      GEL_IBAN,
      { accounts: false, balances: false, transactions: false },
    ],
  ])(
    'grants the services covered by %s',
    (_case, access, iban, expectedServices) => {
      const grantedServices = readGrantedServices(access, iban);

      expect(grantedServices).toEqual(expectedServices);
    },
  );
});
