import {
  InvalidDecimalAmountError,
  formatMinorUnits,
  parseDecimalToMinorUnits,
} from './minor-units.js';

describe('parseDecimalToMinorUnits', () => {
  it.each([
    ['-39.86', -3986],
    ['5623.9', 562390],
    ['880', 88000],
    ['-0.05', -5],
    ['0', 0],
    ['-0.00', 0],
    ['99999999999.99', 9999999999999],
  ])('parses "%s" into %i minor units', (amountText, expectedMinorUnits) => {
    const minorUnits = parseDecimalToMinorUnits(amountText);

    expect(minorUnits).toBe(expectedMinorUnits);
  });

  it.each([
    ['more than two fraction digits', '12.345'],
    ['exponent notation', '1e3'],
    ['an empty text', ''],
    ['a leading space', ' 1'],
    ['a plus sign', '+1.00'],
    ['a decimal comma', '1,50'],
    ['a missing whole part', '.5'],
    ['more minor units than a safe integer holds', '99999999999999.99'],
  ])('rejects an amount with %s', (_case, amountText) => {
    expect(() => parseDecimalToMinorUnits(amountText)).toThrow(
      InvalidDecimalAmountError,
    );
  });
});

describe('formatMinorUnits', () => {
  it.each([
    [-3986, '-39.86'],
    [350000, '3500.00'],
    [-5, '-0.05'],
    [0, '0.00'],
    [562390, '5623.90'],
    [Number.MAX_SAFE_INTEGER, '90071992547409.91'],
  ])('formats %i minor units as "%s"', (minorUnits, expectedText) => {
    const amountText = formatMinorUnits(minorUnits);

    expect(amountText).toBe(expectedText);
  });

  it('round-trips the decimal text of an amount', () => {
    const amountText = formatMinorUnits(parseDecimalToMinorUnits('-1163.3'));

    expect(amountText).toBe('-1163.30');
  });

  it.each([1.5, Number.NaN, Number.POSITIVE_INFINITY])(
    'rejects %f as a number of minor units',
    (minorUnits) => {
      expect(() => formatMinorUnits(minorUnits)).toThrow(RangeError);
    },
  );
});
