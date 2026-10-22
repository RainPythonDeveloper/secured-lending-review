import { applyDecorators, type HttpStatus } from '@nestjs/common';
import {
  ApiExtraModels,
  ApiHeader,
  ApiResponse,
  getSchemaPath,
  type ApiResponseOptions,
} from '@nestjs/swagger';
import { OPEN_BANKING_HEADER } from '../open-banking-headers.js';
import { ProblemDetailsDto } from '../problem-details/dto/problem-details.dto.js';
import {
  PROBLEM_JSON_MEDIA_TYPE,
  describeHttpStatus,
} from '../problem-details/problem-details.js';

type ApiDecorator = MethodDecorator & ClassDecorator;

const DATA_SOURCE_HEADER = 'X-Data-Source';
const DATA_SOURCES = ['tbc-sandbox', 'organizer-dataset'];

export function ApiConsentIdHeader(): ApiDecorator {
  return ApiHeader({
    name: OPEN_BANKING_HEADER.CONSENT_ID,
    required: true,
    description:
      'Identifier of a consent created through POST /v1/consents and authorised by the PSU.',
    schema: { type: 'string', format: 'uuid' },
  });
}

export function ApiPsuIpAddressHeader(): ApiDecorator {
  return ApiHeader({
    name: OPEN_BANKING_HEADER.PSU_IP_ADDRESS,
    required: false,
    description:
      'IP address of the PSU, forwarded to the bank. Defaults to the IP address of the caller.',
    schema: { type: 'string' },
  });
}

export function ApiRequestIdHeader(): ApiDecorator {
  return ApiHeader({
    name: OPEN_BANKING_HEADER.REQUEST_ID,
    required: false,
    description:
      'UUID that correlates the request. Echoed in the response; generated when absent or not a UUID.',
    schema: { type: 'string', format: 'uuid' },
  });
}

export function ApiDataSourceResponseHeader(
  response: ApiResponseOptions,
): ApiDecorator {
  return ApiResponse({
    ...response,
    headers: {
      ...response.headers,
      [DATA_SOURCE_HEADER]: {
        description:
          'Source of the account data served under the consent: the TBC mock sandbox or the organizer dataset.',
        schema: { type: 'string', enum: DATA_SOURCES },
      },
    },
  });
}

export function ApiProblemResponses(...statuses: HttpStatus[]): ApiDecorator {
  return applyDecorators(
    ApiExtraModels(ProblemDetailsDto),
    ...statuses.map((status) =>
      ApiResponse({
        status,
        description: `Problem details (${describeHttpStatus(status)})`,
        content: {
          [PROBLEM_JSON_MEDIA_TYPE]: {
            schema: { $ref: getSchemaPath(ProblemDetailsDto) },
          },
        },
      }),
    ),
  );
}
