export const SYNTHETIC_IBAN_COUNTRY_CODE = 'GE';
// No Georgian bank uses the code XX, so the IBANs are recognisably synthetic yet pass mod-97 validators.
export const SYNTHETIC_IBAN_BANK_CODE = 'XX';

const ACCOUNT_NUMBER_LENGTH = 16;
const DATASET_ACCOUNT_ID_PATTERN = /^ACC-(\d{1,16})$/;
const COUNTRY_CODE_PATTERN = /^[A-Z]{2}$/;
const BBAN_PATTERN = /^[A-Z0-9]{1,30}$/;
const UPPER_CASE_LETTERS_PATTERN = /[A-Z]/g;
// ISO 13616 maps A to 10, B to 11 ... Z to 35.
const LETTER_DIGIT_VALUE_OFFSET = 'A'.charCodeAt(0) - 10;
const CHECK_DIGITS_PLACEHOLDER = '00';
const CHECK_DIGITS_LENGTH = 2;
const IBAN_MODULUS = 97;
const IBAN_CHECK_BASE = 98;
const DECIMAL_BASE = 10;

export function buildSyntheticIban(accountId: string): string {
  const match = DATASET_ACCOUNT_ID_PATTERN.exec(accountId);
  if (match === null) {
    throw new RangeError(
      `Account id ${accountId} does not follow the ACC-<digits> pattern`,
    );
  }
  const [, accountNumber = ''] = match;
  const bban =
    SYNTHETIC_IBAN_BANK_CODE +
    accountNumber.padStart(ACCOUNT_NUMBER_LENGTH, '0');
  const checkDigits = computeIbanCheckDigits(SYNTHETIC_IBAN_COUNTRY_CODE, bban);
  return `${SYNTHETIC_IBAN_COUNTRY_CODE}${checkDigits}${bban}`;
}

// ISO 13616 / ISO 7064 MOD 97-10 over the rearranged IBAN "<bban><country>00".
export function computeIbanCheckDigits(
  countryCode: string,
  bban: string,
): string {
  if (!COUNTRY_CODE_PATTERN.test(countryCode) || !BBAN_PATTERN.test(bban)) {
    throw new RangeError(
      'IBAN parts must be upper-case letters and digits only',
    );
  }
  const rearrangedIban = `${bban}${countryCode}${CHECK_DIGITS_PLACEHOLDER}`;
  const remainder = computeMod97(toIbanDigits(rearrangedIban));
  return String(IBAN_CHECK_BASE - remainder).padStart(CHECK_DIGITS_LENGTH, '0');
}

function toIbanDigits(text: string): string {
  return text.replace(UPPER_CASE_LETTERS_PATTERN, (letter) =>
    String(letter.charCodeAt(0) - LETTER_DIGIT_VALUE_OFFSET),
  );
}

// Digit by digit, so that the running value never leaves the safe integer range.
function computeMod97(digits: string): number {
  let remainder = 0;
  for (const digit of digits) {
    remainder = (remainder * DECIMAL_BASE + Number(digit)) % IBAN_MODULUS;
  }
  return remainder;
}
