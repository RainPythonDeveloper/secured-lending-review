import {
  readConsentIdHeader,
  readPsuIdHeader,
  readPsuIpAddress,
} from './request-headers.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';

const formatError = (detail: string) => ({
  problem: expect.objectContaining({
    status: 400,
    code: 'FORMAT_ERROR',
    detail,
  }),
});

describe('readConsentIdHeader', () => {
  it('returns a UUID Consent-ID', () => {
    const consentId = readConsentIdHeader({ 'consent-id': CONSENT_ID });

    expect(consentId).toBe(CONSENT_ID);
  });

  it.each([
    ['missing', {}],
    ['not a UUID', { 'consent-id': 'consent-1' }],
    ['empty', { 'consent-id': '' }],
  ])('rejects a Consent-ID that is %s with FORMAT_ERROR', (_case, headers) => {
    expect(() => readConsentIdHeader(headers)).toThrow(
      expect.objectContaining(formatError('Consent-ID header must be a UUID')),
    );
  });
});

describe('readPsuIdHeader', () => {
  it('returns undefined when PSU-ID is absent', () => {
    const psuId = readPsuIdHeader({});

    expect(psuId).toBeUndefined();
  });

  it('returns a PSU-ID made of letters, digits and hyphens', () => {
    const psuId = readPsuIdHeader({ 'psu-id': 'CUS-024' });

    expect(psuId).toBe('CUS-024');
  });

  it.each(['CUS 024', 'CUS_024', '', 'C'.repeat(65)])(
    'rejects PSU-ID %j with FORMAT_ERROR',
    (psuId) => {
      expect(() => readPsuIdHeader({ 'psu-id': psuId })).toThrow(
        expect.objectContaining(
          formatError(
            'PSU-ID header must be 1 to 64 letters, digits or hyphens',
          ),
        ),
      );
    },
  );
});

describe('readPsuIpAddress', () => {
  it.each(['203.0.113.7', '2001:db8::7'])(
    'returns the PSU-IP-Address header %s',
    (ipAddress) => {
      const psuIpAddress = readPsuIpAddress(
        { 'psu-ip-address': ipAddress },
        '127.0.0.1',
      );

      expect(psuIpAddress).toBe(ipAddress);
    },
  );

  it('falls back to the request IP address when the header is absent', () => {
    const psuIpAddress = readPsuIpAddress({}, '::ffff:127.0.0.1');

    expect(psuIpAddress).toBe('::ffff:127.0.0.1');
  });

  it('returns undefined when neither the header nor the request IP is known', () => {
    const psuIpAddress = readPsuIpAddress({}, undefined);

    expect(psuIpAddress).toBeUndefined();
  });

  it('rejects a PSU-IP-Address that is not an IP address', () => {
    expect(() =>
      readPsuIpAddress({ 'psu-ip-address': 'localhost' }, '127.0.0.1'),
    ).toThrow(
      expect.objectContaining(
        formatError('PSU-IP-Address header must be an IPv4 or IPv6 address'),
      ),
    );
  });
});
