import type { AccountAccessDto } from '../../shared/dto/account-access.dto.js';

export type AisService = 'accounts' | 'balances' | 'transactions';

// Mirrors the access semantics verified against the TBC sandbox: an absent list grants nothing,
// an empty list grants every account, a non-empty list grants the listed IBANs only.
export function isServiceGranted(
  access: AccountAccessDto,
  service: AisService,
  iban: string,
): boolean {
  if (grantsAvailableAccounts(access)) {
    return isGrantedByAvailableAccounts(access, service);
  }
  const grantedAccounts = access[service];
  if (grantedAccounts === undefined) {
    return false;
  }
  return (
    grantedAccounts.length === 0 ||
    grantedAccounts.some((reference) => reference.iban === iban)
  );
}

function grantsAvailableAccounts(access: AccountAccessDto): boolean {
  return (
    access.availableAccounts !== undefined ||
    access.availableAccountsWithBalance !== undefined
  );
}

// availableAccounts lists every account; only availableAccountsWithBalance adds balances, neither grants transactions.
function isGrantedByAvailableAccounts(
  access: AccountAccessDto,
  service: AisService,
): boolean {
  switch (service) {
    case 'accounts':
      return true;
    case 'balances':
      return access.availableAccountsWithBalance !== undefined;
    case 'transactions':
      return false;
  }
}
