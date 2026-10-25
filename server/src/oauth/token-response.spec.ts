import { loadSandboxFixture } from '../../test/fixtures/load-fixture.js';
import { parseTokenResponse } from './token-response.js';

const tokenFixture = loadSandboxFixture('token.200.json') as Record<
  string,
  unknown
>;

function tokenResponseWith(
  overrides: Record<string, unknown>,
): Record<string, unknown> {
  return { ...tokenFixture, ...overrides };
}

function tokenResponseWithout(fieldName: string): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(tokenFixture).filter(([name]) => name !== fieldName),
  );
}

const contractViolation = (detail: string) =>
  expect.objectContaining({
    problem: expect.objectContaining({
      status: 502,
      code: 'UPSTREAM_CONTRACT_VIOLATION',
      detail: `TBC sandbox token response does not match the specification: ${detail}`,
    }),
  });

describe('parseTokenResponse', () => {
  it('parses the token issued for an authorisation code', () => {
    const issuedTokens = parseTokenResponse(tokenFixture);

    expect(issuedTokens).toEqual({
      accessToken: 'access_fixture-not-a-real-token',
      refreshToken: 'refresh_fixture-not-a-real-token',
      accessTokenLifetimeMs: 3_600_000,
      refreshTokenLifetimeMs: 7_776_000_000,
      scope: 'AIS:3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f',
    });
  });

  it('parses the rotated tokens of a refresh', () => {
    const issuedTokens = parseTokenResponse(
      loadSandboxFixture('token.refreshed.200.json'),
    );

    expect(issuedTokens).toMatchObject({
      accessToken: 'access_fixture-refreshed-not-a-real-token',
      refreshToken: 'refresh_fixture-rotated-not-a-real-token',
    });
  });

  it.each([
    ['a number', 3600, '7776000', 3_600_000, 7_776_000_000],
    ['a digit string', '3600', 7776000, 3_600_000, 7_776_000_000],
  ])(
    'accepts lifetimes given as %s',
    (
      _case,
      expiresIn,
      refreshTokenExpiresIn,
      expectedAccessTokenLifetimeMs,
      expectedRefreshTokenLifetimeMs,
    ) => {
      const body = tokenResponseWith({
        expires_in: expiresIn,
        refresh_token_expires_in: refreshTokenExpiresIn,
      });

      const issuedTokens = parseTokenResponse(body);

      expect(issuedTokens.accessTokenLifetimeMs).toBe(
        expectedAccessTokenLifetimeMs,
      );
      expect(issuedTokens.refreshTokenLifetimeMs).toBe(
        expectedRefreshTokenLifetimeMs,
      );
    },
  );

  it('leaves the refresh token lifetime unknown when the bank omits it', () => {
    const body = tokenResponseWithout('refresh_token_expires_in');

    const issuedTokens = parseTokenResponse(body);

    expect(issuedTokens.refreshTokenLifetimeMs).toBeUndefined();
  });

  it('accepts the Bearer token type in any letter case', () => {
    const body = tokenResponseWith({ token_type: 'bearer' });

    const issuedTokens = parseTokenResponse(body);

    expect(issuedTokens.accessToken).toBe('access_fixture-not-a-real-token');
  });

  it.each([
    ['access_token', 'access_token must be a non-empty string'],
    ['refresh_token', 'refresh_token must be a non-empty string'],
    ['scope', 'scope must be a non-empty string'],
    ['expires_in', 'expires_in must be a whole number of seconds'],
    ['token_type', 'token_type must be Bearer'],
  ])('rejects a token response without %s', (fieldName, expectedIssue) => {
    const body = tokenResponseWithout(fieldName);

    expect(() => parseTokenResponse(body)).toThrow(
      contractViolation(expectedIssue),
    );
  });

  it.each([
    [
      'an empty access token',
      { access_token: '' },
      'access_token must be a non-empty string',
    ],
    ['a MAC token type', { token_type: 'mac' }, 'token_type must be Bearer'],
    [
      'a fractional lifetime',
      { expires_in: 3600.5 },
      'expires_in must be a whole number of seconds',
    ],
    [
      'a negative lifetime',
      { expires_in: -1 },
      'expires_in must be a whole number of seconds',
    ],
    [
      'a non-numeric lifetime text',
      { refresh_token_expires_in: '90d' },
      'refresh_token_expires_in must be a whole number of seconds',
    ],
  ])('rejects a token response with %s', (_case, overrides, expectedIssue) => {
    const body = tokenResponseWith(overrides);

    expect(() => parseTokenResponse(body)).toThrow(
      contractViolation(expectedIssue),
    );
  });

  it.each([
    ['undefined', undefined],
    ['an array', []],
    ['a string', 'token'],
  ])('rejects a token response that is %s', (_case, body) => {
    expect(() => parseTokenResponse(body)).toThrow(
      contractViolation('body is not a JSON object'),
    );
  });
});
