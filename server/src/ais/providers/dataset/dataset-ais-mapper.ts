import type {
  AccountRecord,
  AccountStatus,
  CustomerRecord,
  TransactionRecord,
} from '../../../organizer-dataset/dataset-records.js';
import { formatMinorUnits } from '../../../organizer-dataset/minor-units.js';
import { buildSyntheticIban } from '../../../organizer-dataset/synthetic-iban.js';
import type { AccountDetailsDto } from '../../accounts/dto/account-details.dto.js';
import type { BalanceType } from '../../shared/ais-formats.js';
import type { AccountReferenceDto } from '../../shared/dto/account-reference.dto.js';
import type { AmountDto } from '../../shared/dto/amount.dto.js';
import type { BalanceDto } from '../../shared/dto/balance.dto.js';
import type {
  ReportExchangeRateDto,
  TransactionDto,
} from '../../transactions/dto/transaction.dto.js';
import { buildAccountLinks } from '../account-links.js';

// Only current accounts are exposed through v1 AIS, so every mapped account is one.
const CURRENT_ACCOUNT_NAME = 'Current account';
const CURRENT_ACCOUNT_CASH_ACCOUNT_TYPE = 'CACC';
const PRIVATE_ACCOUNT_USAGE = 'PRIV';
const ACCOUNT_STATUS_BY_DATASET_STATUS: Readonly<
  Record<AccountStatus, string>
> = {
  active: 'enabled',
  closed: 'deleted',
};
// The dataset dictionary defines the available balance of a current account as its booked balance.
const CLOSING_BALANCE_TYPES: readonly BalanceType[] = [
  'interimBooked',
  'interimAvailable',
];
const BALANCE_AFTER_TRANSACTION_TYPE: BalanceType = 'interimBooked';

type CounterpartyFields = Pick<
  TransactionDto,
  'creditorName' | 'creditorAccount' | 'debtorName' | 'debtorAccount'
>;

export function mapAccount(
  account: AccountRecord,
  customer: CustomerRecord,
  balances?: BalanceDto[],
): AccountDetailsDto {
  return {
    resourceId: account.accountId,
    iban: buildSyntheticIban(account.accountId),
    currency: account.currency,
    name: CURRENT_ACCOUNT_NAME,
    ownerName: customer.fullName,
    cashAccountType: CURRENT_ACCOUNT_CASH_ACCOUNT_TYPE,
    status: ACCOUNT_STATUS_BY_DATASET_STATUS[account.status],
    usage: PRIVATE_ACCOUNT_USAGE,
    balances,
    _links: buildAccountLinks(account.accountId),
  };
}

export function mapAccountReference(
  account: AccountRecord,
): AccountReferenceDto {
  return {
    iban: buildSyntheticIban(account.accountId),
    currency: account.currency,
  };
}

export function mapBalances(
  account: AccountRecord,
  referenceDate: string,
): BalanceDto[] {
  return CLOSING_BALANCE_TYPES.map((balanceType) => ({
    balanceType,
    balanceAmount: mapAmount(
      account.currency,
      account.closingBalanceMinorUnits,
    ),
    creditLimitIncluded: false,
    referenceDate,
  }));
}

export function mapTransaction(
  transaction: TransactionRecord,
  relatedAccount?: AccountRecord,
): TransactionDto {
  return {
    transactionId: transaction.transactionId,
    entryReference: String(transaction.postingSequence),
    endToEndId: transaction.transferId ?? undefined,
    bookingDate: transaction.bookingDate,
    valueDate: transaction.bookingDate,
    transactionAmount: mapAmount(
      transaction.currency,
      transaction.amountMinorUnits,
    ),
    ...mapCounterparty(transaction, relatedAccount),
    remittanceInformationUnstructured: transaction.description,
    additionalInformation: transaction.channel,
    proprietaryBankTransactionCode: transaction.category,
    currencyExchange: mapCurrencyExchange(transaction, relatedAccount),
    balanceAfterTransaction: {
      balanceType: BALANCE_AFTER_TRANSACTION_TYPE,
      balanceAmount: mapAmount(
        transaction.currency,
        transaction.balanceAfterMinorUnits,
      ),
    },
  };
}

function mapAmount(currency: string, amountMinorUnits: number): AmountDto {
  return { currency, amount: formatMinorUnits(amountMinorUnits) };
}

// A credit names its payer (debtor), a debit its payee (creditor).
function mapCounterparty(
  transaction: TransactionRecord,
  relatedAccount: AccountRecord | undefined,
): CounterpartyFields {
  const counterpartyAccount =
    relatedAccount === undefined
      ? undefined
      : mapAccountReference(relatedAccount);
  return isCredit(transaction)
    ? {
        debtorName: transaction.counterparty,
        debtorAccount: counterpartyAccount,
      }
    : {
        creditorName: transaction.counterparty,
        creditorAccount: counterpartyAccount,
      };
}

// fx_rate is in destination units per source unit on both legs of a conversion.
function mapCurrencyExchange(
  transaction: TransactionRecord,
  relatedAccount: AccountRecord | undefined,
): ReportExchangeRateDto[] | undefined {
  if (transaction.fxRate === null || relatedAccount === undefined) {
    return undefined;
  }
  const sourceCurrency = isCredit(transaction)
    ? relatedAccount.currency
    : transaction.currency;
  const targetCurrency = isCredit(transaction)
    ? transaction.currency
    : relatedAccount.currency;
  return [
    {
      sourceCurrency,
      exchangeRate: transaction.fxRate,
      unitCurrency: sourceCurrency,
      targetCurrency,
      quotationDate: transaction.bookingDate,
    },
  ];
}

function isCredit(transaction: TransactionRecord): boolean {
  return transaction.amountMinorUnits > 0;
}
