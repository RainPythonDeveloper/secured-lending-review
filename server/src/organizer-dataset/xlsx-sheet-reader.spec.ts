import { OrganizerDatasetFormatError } from './organizer-dataset-errors.js';
import { readCellText } from './xlsx-sheet-reader.js';

const LOCATION = 'sheet Transactions row 2 column amount';

describe('readCellText', () => {
  it.each([
    ['keeps text cells verbatim', '-39.86', '-39.86'],
    ['keeps surrounding spaces of text cells', ' 1 ', ' 1 '],
    [
      'turns date cells into ISO dates',
      new Date('2026-04-22T00:00:00.000Z'),
      '2026-04-22',
    ],
    ['turns empty cells into null', null, null],
    ['turns missing cells into null', undefined, null],
  ])('%s', (_case, value, expectedText) => {
    const text = readCellText(value, LOCATION);

    expect(text).toBe(expectedText);
  });

  it.each([
    ['a boolean', true],
    ['a number', 39.86],
    ['an invalid date', new Date(Number.NaN)],
  ])('rejects %s cell and names its location', (_case, value) => {
    expect(() => readCellText(value, LOCATION)).toThrow(
      new OrganizerDatasetFormatError(
        `Organizer dataset ${LOCATION} holds an unsupported cell value`,
      ),
    );
  });
});
