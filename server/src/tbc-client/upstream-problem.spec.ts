import { readSandboxFixtureText } from '../../test/fixtures/load-fixture.js';
import { createProblem } from '../common/problem-details/problem-details.js';
import { parseUpstreamProblem } from './upstream-problem.js';

describe('parseUpstreamProblem', () => {
  it('keeps a sandbox problem+json body', () => {
    const bodyText = readSandboxFixtureText('problem.consent-invalid.403.json');

    const problem = parseUpstreamProblem(403, bodyText);

    expect(problem).toEqual(JSON.parse(bodyText));
  });

  it.each([
    [
      'token.invalid-grant.400.json',
      'Authorization code is expired, unknown, or already used',
    ],
    ['token.pkce-mismatch.400.json', 'PKCE verifier is incorrect'],
  ])(
    'converts the OAuth error in %s to an uppercased problem code',
    (fileName, expectedDetail) => {
      const problem = parseUpstreamProblem(
        400,
        readSandboxFixtureText(fileName),
      );

      expect(problem).toEqual(
        createProblem({
          status: 400,
          code: 'INVALID_GRANT',
          detail: expectedDetail,
        }),
      );
    },
  );

  it('uses the OAuth error as detail when no description is given', () => {
    const problem = parseUpstreamProblem(400, '{"error":"invalid_scope"}');

    expect(problem).toMatchObject({
      code: 'INVALID_SCOPE',
      detail: 'invalid_scope',
    });
  });

  it.each([
    [502, '<html>Bad gateway</html>', 'SERVICE_UNAVAILABLE'],
    [503, '', 'SERVICE_UNAVAILABLE'],
    [404, '', 'NOT_FOUND'],
    [401, '[]', 'UNAUTHORIZED'],
  ])(
    'falls back for HTTP %i with body %j to code %s',
    (status, bodyText, expectedCode) => {
      const problem = parseUpstreamProblem(status, bodyText);

      expect(problem).toEqual(
        createProblem({
          status,
          code: expectedCode,
          detail: `TBC sandbox answered HTTP ${status} without problem details`,
        }),
      );
    },
  );
});
