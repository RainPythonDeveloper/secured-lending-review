import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AppModule } from '../../src/app.module.js';
import { setupSwagger } from '../../src/common/swagger/setup-swagger.js';
import { GatewayConfig } from '../../src/config/gateway-config.js';
import { OAuthService } from '../../src/oauth/oauth.service.js';
import { FETCH, type FetchFunction } from '../../src/tbc-client/fetch.token.js';
import { TbcClientService } from '../../src/tbc-client/tbc-client.service.js';
import { createFakeTbcClient, type FakeTbcClient } from './fake-tbc-client.js';
import { testGatewayConfig } from './test-gateway-config.js';

export interface TestApp {
  readonly app: INestApplication;
  readonly fakeTbcClient: FakeTbcClient;
  readonly oauthService: OAuthService;
}

const disabledFetch: FetchFunction = () =>
  Promise.reject(new Error('Network access is disabled in tests'));

export async function createTestApp(): Promise<TestApp> {
  const fakeTbcClient = createFakeTbcClient();
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(GatewayConfig)
    .useValue(testGatewayConfig)
    .overrideProvider(TbcClientService)
    .useValue(fakeTbcClient)
    .overrideProvider(FETCH)
    .useValue(disabledFetch)
    .compile();
  const app = moduleRef.createNestApplication();
  setupSwagger(app);
  await app.init();
  return { app, fakeTbcClient, oauthService: app.get(OAuthService) };
}
