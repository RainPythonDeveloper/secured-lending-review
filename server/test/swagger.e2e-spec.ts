import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { createTestApp } from './support/create-test-app.js';

const AIS_DATA_OPERATIONS = [
  '/v1/accounts',
  '/v1/accounts/{accountId}',
  '/v1/accounts/{accountId}/balances',
  '/v1/accounts/{accountId}/transactions',
];

interface DocumentedParameter {
  readonly name: string;
  readonly in: string;
  readonly required?: boolean;
  readonly schema?: Record<string, unknown>;
  readonly example?: unknown;
}

describe('Swagger documentation', () => {
  let app: INestApplication;
  let documentStatus: number;
  let documentText: string;
  let document: {
    info: { title: string; description: string };
    paths: Record<string, Record<string, Record<string, unknown>>>;
    components: { schemas: Record<string, unknown> };
  };

  beforeAll(async () => {
    ({ app } = await createTestApp());
    const response = await request(app.getHttpServer()).get('/api/docs-json');
    documentStatus = response.status;
    documentText = response.text;
    document = response.body;
  });

  afterAll(async () => {
    await app.close();
  });

  function readOperation(path: string, method = 'get') {
    const operation = document.paths[path]?.[method];
    if (operation === undefined) {
      throw new Error(`${method.toUpperCase()} ${path} is not documented`);
    }
    return operation as {
      parameters: DocumentedParameter[];
      responses: Record<
        string,
        { headers?: Record<string, unknown>; content?: Record<string, unknown> }
      >;
    };
  }

  it('serves the OpenAPI document with the gateway title and synthetic data notice', () => {
    expect(documentStatus).toBe(200);
    expect(document.info.title).toBe(
      'Virtual Field Visit - Open Banking AIS gateway',
    );
    expect(document.info.description).toContain(
      'All data served here is synthetic.',
    );
  });

  it('documents exactly the ten gateway operations', () => {
    const operations = Object.entries(document.paths).flatMap(
      ([path, methods]) =>
        Object.keys(methods).map((method) => `${method} ${path}`),
    );

    expect(operations.sort()).toEqual(
      [
        'get /health',
        'get /oauth/callback',
        'post /v1/consents',
        'get /v1/consents/{consentId}',
        'delete /v1/consents/{consentId}',
        'get /v1/consents/{consentId}/status',
        'get /v1/accounts',
        'get /v1/accounts/{accountId}',
        'get /v1/accounts/{accountId}/balances',
        'get /v1/accounts/{accountId}/transactions',
      ].sort(),
    );
  });

  it('documents the X-Data-Source header on consent creation', () => {
    expect(
      readOperation('/v1/consents', 'post').responses['201']?.headers,
    ).toHaveProperty('X-Data-Source');
  });

  it.each(AIS_DATA_OPERATIONS)(
    'documents the X-Data-Source header on GET %s',
    (path) => {
      expect(readOperation(path).responses['200']?.headers).toHaveProperty(
        'X-Data-Source',
      );
    },
  );

  it.each(AIS_DATA_OPERATIONS)(
    'documents problem+json responses on GET %s',
    (path) => {
      const { responses } = readOperation(path);

      expect(Object.keys(responses).sort()).toEqual(
        ['200', '400', '401', '403', '404', '502', '504'].sort(),
      );
      expect(responses['401']?.content).toHaveProperty(
        'application/problem+json',
      );
    },
  );

  it.each(AIS_DATA_OPERATIONS)(
    'requires a Consent-ID header without a default value on GET %s',
    (path) => {
      const consentIdHeader = readOperation(path).parameters.find(
        (parameter) =>
          parameter.in === 'header' && parameter.name === 'Consent-ID',
      );

      expect(consentIdHeader).toMatchObject({
        required: true,
        schema: { type: 'string', format: 'uuid' },
      });
      expect(consentIdHeader?.schema).not.toHaveProperty('default');
      expect(consentIdHeader).not.toHaveProperty('example');
    },
  );

  it('documents the transaction query parameters', () => {
    const queryParameterNames = readOperation(
      '/v1/accounts/{accountId}/transactions',
    )
      .parameters.filter((parameter) => parameter.in === 'query')
      .map((parameter) => parameter.name);

    expect(queryParameterNames.sort()).toEqual(
      ['bookingStatus', 'dateFrom', 'dateTo'].sort(),
    );
  });

  it.each([
    'AccountListDto',
    'AccountDetailsDto',
    'AccountDetailsResponseDto',
    'BalanceDto',
    'AmountDto',
    'ReadAccountBalanceResponseDto',
    'TransactionsResponseDto',
    'AccountReportDto',
    'TransactionDto',
    'ReportExchangeRateDto',
    'ProblemDetailsDto',
  ])('documents the %s schema', (schemaName) => {
    expect(document.components.schemas).toHaveProperty(schemaName);
  });

  it('documents amounts as strings', () => {
    expect(document.components.schemas.AmountDto).toMatchObject({
      properties: { amount: { type: 'string' } },
    });
  });

  it('contains no bearer token, no token values and no consent id defaults', () => {
    expect(documentText).not.toContain('Bearer ');
    expect(documentText).not.toContain('access_');
    expect(documentText).not.toContain('3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f');
  });
});
