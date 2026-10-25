import request from 'supertest';
import { ProblemDetailsException } from '../src/common/problem-details/problem-details.js';
import { parseUpstreamProblem } from '../src/tbc-client/upstream-problem.js';
import { readSandboxFixtureText } from './fixtures/load-fixture.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';

const FIXTURE_CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const UNKNOWN_STATE = '5b4a3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d';
const AUTHORISATION_CODE = 'code_fixture-not-a-real-code';
const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';

describe('OAuth callback', () => {
  let testApp: TestApp;

  beforeEach(async () => {
    testApp = await createTestApp();
  });

  afterEach(async () => {
    await testApp.app.close();
  });

  function startAuthorisationState(): string {
    const authorisationUrl =
      testApp.oauthService.startAuthorisation(FIXTURE_CONSENT_ID);
    return new URL(authorisationUrl).searchParams.get('state') ?? '';
  }

  function callBack(query: Record<string, string>) {
    return request(testApp.app.getHttpServer())
      .get('/oauth/callback')
      .query(query);
  }

  it('finalises the authorisation without returning any token', async () => {
    const state = startAuthorisationState();

    const response = await callBack({ state, code: AUTHORISATION_CODE });

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      consentId: FIXTURE_CONSENT_ID,
      scaStatus: 'finalised',
    });
    expect(response.text).not.toContain('access_fixture');
    expect(response.text).not.toContain('refresh_fixture');
  });

  it('rejects a state that was already used with 400 STATE_INVALID', async () => {
    const state = startAuthorisationState();
    await callBack({ state, code: AUTHORISATION_CODE });

    const response = await callBack({ state, code: AUTHORISATION_CODE });

    expect(response.status).toBe(400);
    expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
    expect(response.body.code).toBe('STATE_INVALID');
  });

  it('rejects an unknown state with 400 STATE_INVALID', async () => {
    const response = await callBack({
      state: UNKNOWN_STATE,
      code: AUTHORISATION_CODE,
    });

    expect(response.status).toBe(400);
    expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
    expect(response.body.code).toBe('STATE_INVALID');
  });

  it('rejects a state that is not a UUID with 400 FORMAT_ERROR', async () => {
    const response = await callBack({
      state: 'state-1',
      code: AUTHORISATION_CODE,
    });

    expect(response.status).toBe(400);
    expect(response.body.code).toBe('FORMAT_ERROR');
  });

  it('answers 403 ACCESS_DENIED when the PSU rejected the consent at the bank', async () => {
    const state = startAuthorisationState();

    const response = await callBack({ state, error: 'access_denied' });

    expect(response.status).toBe(403);
    expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
    expect(response.body.code).toBe('ACCESS_DENIED');
  });

  it('renders the bank invalid_grant answer as 400 INVALID_GRANT problem+json', async () => {
    testApp.fakeTbcClient.exchangeAuthorisationCode.mockRejectedValue(
      new ProblemDetailsException(
        parseUpstreamProblem(
          400,
          readSandboxFixtureText('token.invalid-grant.400.json'),
        ),
      ),
    );
    const state = startAuthorisationState();

    const response = await callBack({ state, code: AUTHORISATION_CODE });

    expect(response.status).toBe(400);
    expect(response.headers['content-type']).toBe(PROBLEM_CONTENT_TYPE);
    expect(response.body).toMatchObject({
      code: 'INVALID_GRANT',
      detail: 'Authorization code is expired, unknown, or already used',
    });
  });
});
