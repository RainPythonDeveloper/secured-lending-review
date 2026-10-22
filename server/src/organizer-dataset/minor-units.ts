const DECIMAL_AMOUNT_PATTERN = /^(-?)(\d{1,14})(?:\.(\d{1,2}))?$/;
const MINOR_UNITS_PER_UNIT = 100;
const MINOR_UNIT_DIGITS = 2;

export class InvalidDecimalAmountError extends Error {
  constructor(readonly amountText: string) {
    super(
      `"${amountText}" is not a decimal amount with at most ${MINOR_UNIT_DIGITS} fraction digits`,
    );
    this.name = 'InvalidDecimalAmountError';
  }
}

// Amounts travel as exact decimal text and integer minor units, never as binary floating point.
export function parseDecimalToMinorUnits(amountText: string): number {
  const match = DECIMAL_AMOUNT_PATTERN.exec(amountText);
  if (match === null) {
    throw new InvalidDecimalAmountError(amountText);
  }
  const [, sign, wholeUnitsText = '', fractionText = ''] = match;
  const absoluteMinorUnits =
    Number(wholeUnitsText) * MINOR_UNITS_PER_UNIT +
    Number(fractionText.padEnd(MINOR_UNIT_DIGITS, '0'));
  if (!Number.isSafeInteger(absoluteMinorUnits)) {
    throw new InvalidDecimalAmountError(amountText);
  }
  const isNegative = sign === '-' && absoluteMinorUnits !== 0;
  return isNegative ? -absoluteMinorUnits : absoluteMinorUnits;
}

export function formatMinorUnits(minorUnits: number): string {
  if (!Number.isSafeInteger(minorUnits)) {
    throw new RangeError(`${minorUnits} is not a whole number of minor units`);
  }
  const absoluteMinorUnits = Math.abs(minorUnits);
  const fractionMinorUnits = absoluteMinorUnits % MINOR_UNITS_PER_UNIT;
  const wholeUnits =
    (absoluteMinorUnits - fractionMinorUnits) / MINOR_UNITS_PER_UNIT;
  const sign = minorUnits < 0 ? '-' : '';
  const fractionText = String(fractionMinorUnits).padStart(
    MINOR_UNIT_DIGITS,
    '0',
  );
  return `${sign}${wholeUnits}.${fractionText}`;
}
