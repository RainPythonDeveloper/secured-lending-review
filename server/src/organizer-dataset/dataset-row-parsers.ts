import {
  ACCOUNT_STATUSES,
  ACCOUNT_TYPES,
  type AccountRecord,
  type CustomerRecord,
  type TransactionRecord,
} from './dataset-records.js';
import {
  InvalidDecimalAmountError,
  parseDecimalToMinorUnits,
} from './minor-units.js';
import { OrganizerDatasetFormatError } from './organizer-dataset-errors.js';
import type { DatasetRow } from './xlsx-sheet-reader.js';

const CUSTOMER_ID_PATTERN = /^CUS-\d{1,16}$/;
const DATASET_ACCOUNT_ID_PATTERN = /^ACC-\d{1,16}$/;
const TRANSACTION_ID_PATTERN = /^TX-\d{1,16}$/;
const CURRENCY_CODE_PATTERN = /^[A-Z]{3}$/;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const POSTING_SEQUENCE_PATTERN = /^\d{1,15}$/;
const FX_RATE_PATTERN = /^\d{1,6}(\.\d{1,8})?$/;

export function parseCustomerRow(row: DatasetRow): CustomerRecord {
  return {
    customerId: readMatchingText(row, 'customer_id', CUSTOMER_ID_PATTERN),
    fullName: readRequiredText(row, 'full_name'),
  };
}

export function parseAccountRow(row: DatasetRow): AccountRecord {
  return {
    accountId: readMatchingText(row, 'account_id', DATASET_ACCOUNT_ID_PATTERN),
    customerId: readMatchingText(row, 'customer_id', CUSTOMER_ID_PATTERN),
    accountType: readOneOf(row, 'account_type', ACCOUNT_TYPES),
    currency: readMatchingText(row, 'currency', CURRENCY_CODE_PATTERN),
    status: readOneOf(row, 'status', ACCOUNT_STATUSES),
    openingBalanceMinorUnits: readMinorUnits(row, 'opening_balance'),
    closingBalanceMinorUnits: readMinorUnits(row, 'closing_balance'),
  };
}

export function parseTransactionRow(row: DatasetRow): TransactionRecord {
  return {
    transactionId: readMatchingText(
      row,
      'transaction_id',
      TRANSACTION_ID_PATTERN,
    ),
    accountId: readMatchingText(row, 'account_id', DATASET_ACCOUNT_ID_PATTERN),
    bookingDate: readMatchingText(row, 'booking_date', ISO_DATE_PATTERN),
    postingSequence: Number(
      readMatchingText(row, 'posting_sequence', POSTING_SEQUENCE_PATTERN),
    ),
    currency: readMatchingText(row, 'currency', CURRENCY_CODE_PATTERN),
    category: readRequiredText(row, 'category'),
    amountMinorUnits: readMinorUnits(row, 'amount'),
    balanceAfterMinorUnits: readMinorUnits(row, 'balance_after'),
    channel: readRequiredText(row, 'channel'),
    counterparty: readRequiredText(row, 'counterparty'),
    description: readRequiredText(row, 'description'),
    transferId: readOptionalText(row, 'transfer_id'),
    relatedAccountId: readOptionalMatchingText(
      row,
      'related_account_id',
      DATASET_ACCOUNT_ID_PATTERN,
    ),
    fxRate: readOptionalMatchingText(row, 'fx_rate', FX_RATE_PATTERN),
  };
}

function readOptionalText(row: DatasetRow, columnName: string): string | null {
  const text = row.cells[columnName];
  return text === undefined || text === null || text === '' ? null : text;
}

function readRequiredText(row: DatasetRow, columnName: string): string {
  const text = readOptionalText(row, columnName);
  if (text === null) {
    throw createRowError(row, `${columnName} is required`);
  }
  return text;
}

function readOptionalMatchingText(
  row: DatasetRow,
  columnName: string,
  pattern: RegExp,
): string | null {
  const text = readOptionalText(row, columnName);
  if (text !== null && !pattern.test(text)) {
    throw createRowError(row, `${columnName} "${text}" is malformed`);
  }
  return text;
}

function readMatchingText(
  row: DatasetRow,
  columnName: string,
  pattern: RegExp,
): string {
  const text = readRequiredText(row, columnName);
  if (!pattern.test(text)) {
    throw createRowError(row, `${columnName} "${text}" is malformed`);
  }
  return text;
}

function readOneOf<Value extends string>(
  row: DatasetRow,
  columnName: string,
  allowedValues: readonly Value[],
): Value {
  const text = readRequiredText(row, columnName);
  const value = allowedValues.find((allowedValue) => allowedValue === text);
  if (value === undefined) {
    throw createRowError(
      row,
      `${columnName} "${text}" is not one of ${allowedValues.join(', ')}`,
    );
  }
  return value;
}

function readMinorUnits(row: DatasetRow, columnName: string): number {
  const text = readRequiredText(row, columnName);
  try {
    return parseDecimalToMinorUnits(text);
  } catch (error) {
    if (error instanceof InvalidDecimalAmountError) {
      throw createRowError(row, `${columnName} ${error.message}`);
    }
    throw error;
  }
}

function createRowError(
  row: DatasetRow,
  issue: string,
): OrganizerDatasetFormatError {
  return new OrganizerDatasetFormatError(
    `Organizer dataset sheet ${row.sheetName} row ${row.rowNumber}: ${issue}`,
  );
}
