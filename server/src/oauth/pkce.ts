import { createHash, randomBytes } from 'node:crypto';

// RFC 7636 §4.1: 32 random octets give a 43-character base64url verifier.
const CODE_VERIFIER_BYTE_LENGTH = 32;

export interface PkcePair {
  readonly codeVerifier: string;
  readonly codeChallenge: string;
}

export function createPkcePair(): PkcePair {
  const codeVerifier = randomBytes(CODE_VERIFIER_BYTE_LENGTH).toString(
    'base64url',
  );
  return { codeVerifier, codeChallenge: computeCodeChallenge(codeVerifier) };
}

export function computeCodeChallenge(codeVerifier: string): string {
  return createHash('sha256').update(codeVerifier).digest('base64url');
}
