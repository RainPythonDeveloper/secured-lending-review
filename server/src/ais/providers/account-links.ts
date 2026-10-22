import type { AccountLinksDto } from '../accounts/dto/account-details.dto.js';
import type { TransactionLinksDto } from '../transactions/dto/transactions-response.dto.js';

const ACCOUNTS_PATH = '/v1/accounts';

export function buildAccountLinks(resourceId: string): AccountLinksDto {
  const accountPath = buildAccountPath(resourceId);
  return {
    account: { href: accountPath },
    balances: { href: `${accountPath}/balances` },
    transactions: { href: `${accountPath}/transactions` },
  };
}

export function buildTransactionLinks(resourceId: string): TransactionLinksDto {
  return { account: { href: buildAccountPath(resourceId) } };
}

function buildAccountPath(resourceId: string): string {
  return `${ACCOUNTS_PATH}/${encodeURIComponent(resourceId)}`;
}
