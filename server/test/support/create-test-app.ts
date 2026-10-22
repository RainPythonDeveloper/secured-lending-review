import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AppModule } from '../../src/app.module.js';
import { GatewayConfig } from '../../src/config/gateway-config.js';
import { testGatewayConfig } from './test-gateway-config.js';

export async function createTestApp(): Promise<INestApplication> {
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(GatewayConfig)
    .useValue(testGatewayConfig)
    .compile();
  const app = moduleRef.createNestApplication();
  await app.init();
  return app;
}
