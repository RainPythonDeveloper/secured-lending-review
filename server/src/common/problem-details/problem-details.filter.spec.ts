import {
  BadRequestException,
  HttpStatus,
  Logger,
  MethodNotAllowedException,
  NotFoundException,
  type ArgumentsHost,
} from '@nestjs/common';
import { ProblemDetailsFilter } from './problem-details.filter.js';
import {
  PROBLEM_JSON_CONTENT_TYPE,
  ProblemDetailsException,
  createProblem,
} from './problem-details.js';

const GATEWAY_REQUEST_ID = '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c';

interface RenderedResponse {
  statusCode?: number;
  contentType?: string;
  body?: unknown;
}

function renderWithFilter(exception: unknown): RenderedResponse {
  const rendered: RenderedResponse = {};
  const response = {
    locals: { gatewayRequestId: GATEWAY_REQUEST_ID },
    status(statusCode: number) {
      rendered.statusCode = statusCode;
      return this;
    },
    type(contentType: string) {
      rendered.contentType = contentType;
      return this;
    },
    json(body: unknown) {
      rendered.body = body;
      return this;
    },
  };
  const host = {
    switchToHttp: () => ({ getResponse: () => response }),
  } as unknown as ArgumentsHost;
  new ProblemDetailsFilter().catch(exception, host);
  return rendered;
}

describe('ProblemDetailsFilter', () => {
  let loggedErrors: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    loggedErrors = vi
      .spyOn(Logger.prototype, 'error')
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a ProblemDetailsException unchanged as problem+json', () => {
    const problem = createProblem({
      status: HttpStatus.FORBIDDEN,
      code: 'CONSENT_INVALID',
      detail: 'Consent does not allow transactions for this account',
    });

    const rendered = renderWithFilter(new ProblemDetailsException(problem));

    expect(rendered).toEqual({
      statusCode: 403,
      contentType: PROBLEM_JSON_CONTENT_TYPE,
      body: problem,
    });
  });

  it('maps ValidationPipe errors to FORMAT_ERROR with one tppMessage per message', () => {
    const exception = new BadRequestException([
      'frequencyPerDay must not be greater than 4',
      'access.property Accounts should not exist',
    ]);

    const rendered = renderWithFilter(exception);

    expect(rendered.statusCode).toBe(400);
    expect(rendered.body).toEqual({
      type: 'about:blank',
      title: 'FORMAT_ERROR',
      status: 400,
      code: 'FORMAT_ERROR',
      detail:
        'frequencyPerDay must not be greater than 4; access.property Accounts should not exist',
      tppMessages: [
        {
          category: 'ERROR',
          code: 'FORMAT_ERROR',
          text: 'frequencyPerDay must not be greater than 4',
        },
        {
          category: 'ERROR',
          code: 'FORMAT_ERROR',
          text: 'access.property Accounts should not exist',
        },
      ],
    });
  });

  it('maps an unknown route to 404 RESOURCE_UNKNOWN', () => {
    const rendered = renderWithFilter(
      new NotFoundException('Cannot GET /nope'),
    );

    expect(rendered.statusCode).toBe(404);
    expect(rendered.body).toEqual(
      createProblem({
        status: 404,
        code: 'RESOURCE_UNKNOWN',
        detail: 'Cannot GET /nope',
      }),
    );
  });

  it('names the code of other HTTP exceptions after their status', () => {
    const rendered = renderWithFilter(new MethodNotAllowedException());

    expect(rendered.statusCode).toBe(405);
    expect(rendered.body).toMatchObject({
      status: 405,
      code: 'METHOD_NOT_ALLOWED',
    });
  });

  it('hides unknown errors behind a generic 500 INTERNAL_ERROR without the stack', () => {
    const rendered = renderWithFilter(new Error('database password is wrong'));

    expect(rendered).toEqual({
      statusCode: 500,
      contentType: PROBLEM_JSON_CONTENT_TYPE,
      body: createProblem({
        status: 500,
        code: 'INTERNAL_ERROR',
        detail: 'The gateway failed to process the request',
      }),
    });
  });

  it('logs unknown errors with the gateway request id and stack', () => {
    const error = new Error('unexpected failure');

    renderWithFilter(error);

    expect(loggedErrors).toHaveBeenCalledWith(
      `Unhandled error while serving request ${GATEWAY_REQUEST_ID}`,
      error.stack,
    );
  });
});
