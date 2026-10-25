import { ProblemDetailsException } from '../../src/common/problem-details/problem-details.js';
import { parseUpstreamProblem } from '../../src/tbc-client/upstream-problem.js';
import {
  loadSandboxFixture,
  readSandboxFixtureText,
} from '../fixtures/load-fixture.js';
import { bankOfferedConsentRequest } from './authorise-consent.js';

// What TbcClientService rejects with when the bank answers with the given problem fixture.
export function upstreamProblem(
  status: number,
  fixtureFileName: string,
): ProblemDetailsException {
  return new ProblemDetailsException(
    parseUpstreamProblem(status, readSandboxFixtureText(fixtureFileName)),
  );
}

// The bank keeps the access of a consent created with bankOfferedConsentRequest as empty arrays.
export function upstreamConsentDetails(
  changes: Record<string, unknown> = {},
): unknown {
  return {
    ...(loadSandboxFixture('consent-details.200.json') as object),
    access: bankOfferedConsentRequest.access,
    ...changes,
  };
}
