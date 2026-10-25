import { computeCodeChallenge, createPkcePair } from './pkce.js';

const BASE64URL_VERIFIER_PATTERN = /^[A-Za-z0-9_-]{43}$/;

describe('PKCE', () => {
  it('computes the S256 challenge of the RFC 7636 Appendix B verifier', () => {
    const codeChallenge = computeCodeChallenge(
      'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk',
    );

    expect(codeChallenge).toBe('E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM');
  });

  it('creates a 43-character base64url code verifier', () => {
    const { codeVerifier } = createPkcePair();

    expect(codeVerifier).toMatch(BASE64URL_VERIFIER_PATTERN);
  });

  it('pairs the code verifier with its S256 challenge', () => {
    const { codeVerifier, codeChallenge } = createPkcePair();

    expect(codeChallenge).toBe(computeCodeChallenge(codeVerifier));
  });

  it('creates a different code verifier for every authorisation', () => {
    const firstPair = createPkcePair();
    const secondPair = createPkcePair();

    expect(firstPair.codeVerifier).not.toBe(secondPair.codeVerifier);
  });
});
