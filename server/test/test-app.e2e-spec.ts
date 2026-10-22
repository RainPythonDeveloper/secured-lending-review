import { FETCH, type FetchFunction } from '../src/tbc-client/fetch.token.js';
import { TbcClientService } from '../src/tbc-client/tbc-client.service.js';
import { TbcHttpTransport } from '../src/tbc-client/tbc-http-transport.js';
import { createTestApp, type TestApp } from './support/create-test-app.js';
import { loadSandboxFixture } from './fixtures/load-fixture.js';

describe('e2e test application', () => {
  let testApp: TestApp;

  beforeAll(async () => {
    testApp = await createTestApp();
  });

  afterAll(async () => {
    await testApp.app.close();
  });

  it('serves the TBC client from the fixture-backed fake', async () => {
    const tbcClient = testApp.app.get(TbcClientService);

    const consent = await tbcClient.getConsentStatus('consent', {
      gatewayRequestId: 'request',
    });

    expect(tbcClient).toBe(testApp.fakeTbcClient);
    expect(consent).toEqual(
      loadSandboxFixture('consent-status.valid.200.json'),
    );
  });

  it('refuses network access through the injected fetch', async () => {
    const fetchFunction = testApp.app.get<FetchFunction>(FETCH);

    const fetching = fetchFunction('https://example.invalid');

    await expect(fetching).rejects.toThrow(
      'Network access is disabled in tests',
    );
  });

  it('builds the HTTP transport on top of the disabled fetch', async () => {
    const transport = testApp.app.get(TbcHttpTransport);

    const sending = transport.send({
      operationName: 'getConsent',
      method: 'GET',
      url: 'https://example.invalid/v1/consents/consent',
      headers: {},
      context: { gatewayRequestId: 'request' },
    });

    await expect(sending).rejects.toThrow(
      'Network access is disabled in tests',
    );
  });
});
