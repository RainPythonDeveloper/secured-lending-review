import {
  buildSyntheticIban,
  computeIbanCheckDigits,
} from './synthetic-iban.js';

// Independent ISO 13616 check: move the first four characters to the end, map letters to 10..35, mod 97.
function computeIbanRemainder(iban: string): bigint {
  const rearrangedIban = iban.slice(4) + iban.slice(0, 4);
  const digits = rearrangedIban.replace(/[A-Z]/g, (letter) =>
    parseInt(letter, 36).toString(),
  );
  return BigInt(digits) % 97n;
}

describe('computeIbanCheckDigits', () => {
  it.each([
    ['GE', 'NB0000000101904917', '29'],
    ['GB', 'WEST12345698765432', '82'],
  ])(
    'computes the check digits of the %s IBAN with BBAN %s as %s',
    (countryCode, bban, expectedCheckDigits) => {
      const checkDigits = computeIbanCheckDigits(countryCode, bban);

      expect(checkDigits).toBe(expectedCheckDigits);
    },
  );

  it.each([
    ['ge', 'NB0000000101904917'],
    ['GE', 'nb0000000101904917'],
    ['GE', 'NB-0001'],
  ])('rejects the IBAN parts %s and %s', (countryCode, bban) => {
    expect(() => computeIbanCheckDigits(countryCode, bban)).toThrow(RangeError);
  });
});

describe('buildSyntheticIban', () => {
  it.each([
    ['ACC-0024', 'GE38XX0000000000000024'],
    ['ACC-0143', 'GE26XX0000000000000143'],
    ['ACC-0011', 'GE98XX0000000000000011'],
    ['ACC-0179', 'GE24XX0000000000000179'],
  ])('builds the synthetic IBAN of %s as %s', (accountId, expectedIban) => {
    const iban = buildSyntheticIban(accountId);

    expect(iban).toBe(expectedIban);
  });

  it('builds the same IBAN for the same account every time', () => {
    const firstIban = buildSyntheticIban('ACC-0024');
    const secondIban = buildSyntheticIban('ACC-0024');

    expect(secondIban).toBe(firstIban);
  });

  it.each(['ACC-0001', 'ACC-0024', 'ACC-0226', 'ACC-9999999999999999'])(
    'builds an IBAN for %s that passes the mod-97 check',
    (accountId) => {
      const iban = buildSyntheticIban(accountId);

      expect(computeIbanRemainder(iban)).toBe(1n);
    },
  );

  it.each([
    'ACC-',
    'acc-0024',
    'CUS-024',
    'ACC-0024-1',
    'ACC-12345678901234567',
  ])('rejects the malformed account id %s', (accountId) => {
    expect(() => buildSyntheticIban(accountId)).toThrow(RangeError);
  });
});
