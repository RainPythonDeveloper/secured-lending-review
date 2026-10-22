import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { createTestApp } from './support/create-test-app.js';

describe('Swagger documentation', () => {
  let app: INestApplication;

  beforeAll(async () => {
    app = await createTestApp();
  });

  afterAll(async () => {
    await app.close();
  });

  it('serves the OpenAPI document with the gateway title and synthetic data notice', async () => {
    const response = await request(app.getHttpServer()).get('/api/docs-json');

    expect(response.status).toBe(200);
    expect(response.body.info.title).toBe(
      'Virtual Field Visit - Open Banking AIS gateway',
    );
    expect(response.body.info.description).toContain(
      'All data served here is synthetic.',
    );
  });

  it('documents the health endpoint', async () => {
    const response = await request(app.getHttpServer()).get('/api/docs-json');

    expect(response.body.paths['/health']).toHaveProperty('get');
  });
});
