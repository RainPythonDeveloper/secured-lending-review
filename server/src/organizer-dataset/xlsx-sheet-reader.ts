import { readSheet } from 'read-excel-file/node';
import { OrganizerDatasetFormatError } from './organizer-dataset-errors.js';

export type DatasetCell = string | null;

export interface DatasetRow {
  readonly sheetName: string;
  readonly rowNumber: number;
  readonly cells: Readonly<Record<string, DatasetCell>>;
}

// Row 1 of every sheet holds the column names.
const FIRST_DATA_ROW_NUMBER = 2;
const ISO_DATE_LENGTH = 'YYYY-MM-DD'.length;

// Numbers stay as their exact XML text, so amounts never pass through binary floating point.
const READ_OPTIONS = {
  parseNumber: (text: string): string => text,
  trim: false,
};

export async function readSheetRows(
  filePath: string,
  sheetName: string,
): Promise<DatasetRow[]> {
  const sheetData: readonly (readonly unknown[])[] = await readSheet(
    filePath,
    sheetName,
    READ_OPTIONS,
  );
  const [headerRow, ...dataRows] = sheetData;
  if (headerRow === undefined) {
    throw new OrganizerDatasetFormatError(
      `Organizer dataset sheet ${sheetName} has no header row`,
    );
  }
  const columnNames = headerRow.map((cell, columnIndex) =>
    readColumnName(cell, `sheet ${sheetName} column ${columnIndex + 1}`),
  );
  return dataRows.map((cellValues, index) =>
    toDatasetRow(
      sheetName,
      index + FIRST_DATA_ROW_NUMBER,
      columnNames,
      cellValues,
    ),
  );
}

function toDatasetRow(
  sheetName: string,
  rowNumber: number,
  columnNames: readonly string[],
  cellValues: readonly unknown[],
): DatasetRow {
  const cells = columnNames.map((columnName, columnIndex) => [
    columnName,
    readCellText(
      cellValues[columnIndex],
      `sheet ${sheetName} row ${rowNumber} column ${columnName}`,
    ),
  ]);
  return { sheetName, rowNumber, cells: Object.fromEntries(cells) };
}

// The library's typings declare date cells as `typeof Date`; at runtime they are Date instances at UTC midnight.
export function readCellText(value: unknown, location: string): DatasetCell {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'string') {
    return value;
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString().slice(0, ISO_DATE_LENGTH);
  }
  throw new OrganizerDatasetFormatError(
    `Organizer dataset ${location} holds an unsupported cell value`,
  );
}

function readColumnName(value: unknown, location: string): string {
  if (typeof value !== 'string' || value === '') {
    throw new OrganizerDatasetFormatError(
      `Organizer dataset ${location} has no column name`,
    );
  }
  return value;
}
