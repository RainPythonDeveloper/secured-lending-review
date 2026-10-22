import type { INestApplication } from '@nestjs/common';
import { isUUID } from 'class-validator';
import request from 'supertest';
import { createTestApp } from './support/create-test-app.js';

const CALLER_REQUEST_ID = '0f1e2d3c-4b5a-4968-8776-655443322110';

describe('Gateway error responses', () => {
  let app: INestApplication;

  beforeAll(async () => {
    ({ app } = await createTestApp());
  });

  afterAll(async () => {
    await app.close();
  });

  it('renders an unknown route as problem+json 404 RESOURCE_UNKNOWN', async () => {
    const response = await request(app.getHttpServer()).get('/nope');

    expect(response.status).toBe(404);
    expect(response.headers['content-type']).toBe(
      'application/problem+json; charset=utf-8',
    );
    expect(isUUID(response.headers['x-request-id'], 4)).toBe(true);
    expect(JSON.parse(response.text)).toEqual({
      type: 'about:blank',
      title: 'RESOURCE_UNKNOWN',
      status: 404,
      code: 'RESOURCE_UNKNOWN',
      detail: 'Cannot GET /nope',
      tppMessages: [
        {
          category: 'ERROR',
          code: 'RESOURCE_UNKNOWN',
          text: 'Cannot GET /nope',
        },
      ],
    });
  });

  it('echoes a UUID X-Request-ID sent by the caller', async () => {
    const response = await request(app.getHttpServer())
      .get('/nope')
      .set('X-Request-ID', CALLER_REQUEST_ID);

    expect(response.headers['x-request-id']).toBe(CALLER_REQUEST_ID);
  });

  it('replaces an X-Request-ID that is not a UUID with a generated one', async () => {
    const response = await request(app.getHttpServer())
      .get('/health')
      .set('X-Request-ID', 'request-42');

    expect(response.headers['x-request-id']).not.toBe('request-42');
    expect(isUUID(response.headers['x-request-id'], 4)).toBe(true);
  });
});
