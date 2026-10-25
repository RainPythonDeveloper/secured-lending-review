// Formats of the TBC sandbox OpenAPI specification (Berlin Group NextGenPSD2), shared by every AIS DTO.
export const AMOUNT_PATTERN = /^-?[0-9]{1,14}(\.[0-9]{1,3})?$/;
export const CURRENCY_CODE_PATTERN = /^[A-Z]{3}$/;
export const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
export const ACCOUNT_ID_PATTERN = /^[A-Za-z0-9-]{1,64}$/;
// Shape only, no mod-97 check: the sandbox's own IBANs fail the ISO 13616 checksum.
export const IBAN_PATTERN = /^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$/;
export const BBAN_PATTERN = /^[A-Za-z0-9]{1,30}$/;
export const MASKED_PAN_MAX_LENGTH = 35;

export const CONSENT_STATUSES = [
  'received',
  'rejected',
  'valid',
  'revokedByPsu',
  'expired',
  'terminatedByTpp',
] as const;
export const BOOKING_STATUSES = ['booked', 'pending', 'both'] as const;
export const BALANCE_TYPES = [
  'closingBooked',
  'expected',
  'openingBooked',
  'interimAvailable',
  'interimBooked',
  'forwardAvailable',
  'nonInvoiced',
] as const;
export const AVAILABLE_ACCOUNTS_VALUES = [
  'allAccounts',
  'allAccountsWithOwnerName',
] as const;
export const CASH_ACCOUNT_TYPES = ['CACC', 'CARD'] as const;

export type ConsentStatus = (typeof CONSENT_STATUSES)[number];
export type BookingStatus = (typeof BOOKING_STATUSES)[number];
export type BalanceType = (typeof BALANCE_TYPES)[number];
export type AvailableAccountsValue = (typeof AVAILABLE_ACCOUNTS_VALUES)[number];
export type CashAccountType = (typeof CASH_ACCOUNT_TYPES)[number];
