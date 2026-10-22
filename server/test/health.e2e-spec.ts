import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { createTestApp } from './support/create-test-app.js';

describe('GET /health', () => {
  let app: INestApplication;

  beforeAll(async () => {
    app = await createTestApp();
  });

  afterAll(async () => {
    await app.close();
  });

  it('reports the gateway as running', async () => {
    const response = await request(app.getHttpServer()).get('/health');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok' });
  });
});
