import { Controller, Get, HttpStatus } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import {
  ApiProperty,
  DocumentBuilder,
  SwaggerModule,
  type OpenAPIObject,
} from '@nestjs/swagger';
import {
  ApiConsentIdHeader,
  ApiDataSourceResponseHeader,
  ApiProblemResponses,
  ApiPsuIpAddressHeader,
  ApiRequestIdHeader,
} from './api-gateway.decorators.js';

class ProbeResponseDto {
  @ApiProperty()
  readonly value: string;
}

@Controller('probe')
class ProbeController {
  @Get()
  @ApiConsentIdHeader()
  @ApiPsuIpAddressHeader()
  @ApiRequestIdHeader()
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Probe payload',
    type: ProbeResponseDto,
  })
  @ApiProblemResponses(HttpStatus.BAD_REQUEST, HttpStatus.NOT_FOUND)
  readProbe(): ProbeResponseDto {
    return { value: 'probe' };
  }
}

async function buildProbeDocument(): Promise<OpenAPIObject> {
  const moduleRef = await Test.createTestingModule({
    controllers: [ProbeController],
  }).compile();
  const app = moduleRef.createNestApplication({ logger: false });
  const document = SwaggerModule.createDocument(
    app,
    new DocumentBuilder().build(),
  );
  await app.close();
  return document;
}

describe('API gateway Swagger decorators', () => {
  let document: OpenAPIObject;

  beforeAll(async () => {
    document = await buildProbeDocument();
  });

  it('documents Consent-ID as a required UUID header without a default', () => {
    const operation = document.paths['/probe']?.get;

    expect(operation?.parameters).toContainEqual(
      expect.objectContaining({
        name: 'Consent-ID',
        in: 'header',
        required: true,
        schema: { type: 'string', format: 'uuid' },
      }),
    );
  });

  it.each(['PSU-IP-Address', 'X-Request-ID'])(
    'documents %s as an optional request header',
    (headerName) => {
      const operation = document.paths['/probe']?.get;

      expect(operation?.parameters).toContainEqual(
        expect.objectContaining({
          name: headerName,
          in: 'header',
          required: false,
        }),
      );
    },
  );

  it('documents the X-Data-Source header on the success response', () => {
    const successResponse = document.paths['/probe']?.get?.responses['200'];

    expect(successResponse).toMatchObject({
      description: 'Probe payload',
      headers: {
        'X-Data-Source': {
          schema: {
            type: 'string',
            enum: ['tbc-sandbox', 'organizer-dataset'],
          },
        },
      },
    });
  });

  it.each(['400', '404'])(
    'documents the %s response as application/problem+json problem details',
    (status) => {
      const problemResponse = document.paths['/probe']?.get?.responses[status];

      expect(problemResponse).toMatchObject({
        content: {
          'application/problem+json': {
            schema: { $ref: '#/components/schemas/ProblemDetailsDto' },
          },
        },
      });
    },
  );

  it('registers the problem details schema with its tppMessages', () => {
    const schemas = document.components?.schemas;

    expect(Object.keys(schemas ?? {})).toEqual(
      expect.arrayContaining(['ProblemDetailsDto', 'TppMessageDto']),
    );
  });
});
