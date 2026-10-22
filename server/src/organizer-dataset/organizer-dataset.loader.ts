import { Logger } from '@nestjs/common';
import {
  parseAccountRow,
  parseCustomerRow,
  parseTransactionRow,
} from './dataset-row-parsers.js';
import { OrganizerDataset } from './organizer-dataset.js';
import { readSheetRows } from './xlsx-sheet-reader.js';

const CUSTOMERS_SHEET_NAME = 'Customers';
const ACCOUNTS_SHEET_NAME = 'Accounts';
const TRANSACTIONS_SHEET_NAME = 'Transactions';

const logger = new Logger(OrganizerDataset.name);

// Sheets are read one after another to keep the peak memory of the workbook parser low.
export async function loadOrganizerDataset(
  filePath: string,
): Promise<OrganizerDataset> {
  const customerRows = await readSheetRows(filePath, CUSTOMERS_SHEET_NAME);
  const accountRows = await readSheetRows(filePath, ACCOUNTS_SHEET_NAME);
  const transactionRows = await readSheetRows(
    filePath,
    TRANSACTIONS_SHEET_NAME,
  );
  const dataset = OrganizerDataset.fromRecords({
    customers: customerRows.map(parseCustomerRow),
    accounts: accountRows.map(parseAccountRow),
    transactions: transactionRows.map(parseTransactionRow),
  });
  const { customers, accounts, transactions } = dataset.counts;
  logger.log(
    `Organizer dataset loaded: ${customers} customers, ${accounts} accounts, ${transactions} transactions`,
  );
  return dataset;
}
