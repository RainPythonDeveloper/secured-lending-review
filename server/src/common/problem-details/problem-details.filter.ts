import {
  BadRequestException,
  Catch,
  HttpException,
  HttpStatus,
  Logger,
  NotFoundException,
  type ArgumentsHost,
  type ExceptionFilter,
} from '@nestjs/common';
import type { Response } from 'express';
import {
  PROBLEM_CODE,
  PROBLEM_JSON_CONTENT_TYPE,
  ProblemDetailsException,
  createProblem,
  createTppError,
  describeHttpStatus,
  type ProblemDetails,
} from './problem-details.js';

const INTERNAL_ERROR_DETAIL = 'The gateway failed to process the request';
const VALIDATION_MESSAGE_SEPARATOR = '; ';

@Catch()
export class ProblemDetailsFilter implements ExceptionFilter {
  private readonly logger = new Logger(ProblemDetailsFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();
    const problem = this.toProblem(exception, response.locals.gatewayRequestId);
    response
      .status(problem.status)
      .type(PROBLEM_JSON_CONTENT_TYPE)
      .json(problem);
  }

  private toProblem(
    exception: unknown,
    gatewayRequestId: string,
  ): ProblemDetails {
    if (exception instanceof ProblemDetailsException) {
      return exception.problem;
    }
    if (exception instanceof BadRequestException) {
      return toFormatErrorProblem(exception);
    }
    if (exception instanceof NotFoundException) {
      return createProblem({
        status: HttpStatus.NOT_FOUND,
        code: PROBLEM_CODE.RESOURCE_UNKNOWN,
        detail: exception.message,
      });
    }
    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const code = describeHttpStatus(status);
      return createProblem({ status, code, detail: exception.message });
    }
    this.logger.error(
      `Unhandled error while serving request ${gatewayRequestId}`,
      exception instanceof Error ? exception.stack : String(exception),
    );
    return createProblem({
      status: HttpStatus.INTERNAL_SERVER_ERROR,
      code: PROBLEM_CODE.INTERNAL_ERROR,
      detail: INTERNAL_ERROR_DETAIL,
    });
  }
}

function toFormatErrorProblem(exception: BadRequestException): ProblemDetails {
  const messages = readValidationMessages(exception);
  const problem = createProblem({
    status: HttpStatus.BAD_REQUEST,
    code: PROBLEM_CODE.FORMAT_ERROR,
    detail: messages.join(VALIDATION_MESSAGE_SEPARATOR),
  });
  return {
    ...problem,
    tppMessages: messages.map((message) =>
      createTppError(PROBLEM_CODE.FORMAT_ERROR, message),
    ),
  };
}

// ValidationPipe puts its messages into the exception body as `message: string[]`.
function readValidationMessages(exception: BadRequestException): string[] {
  const body = exception.getResponse();
  const message =
    typeof body === 'object' && 'message' in body ? body.message : undefined;
  if (Array.isArray(message)) {
    return message.filter((item): item is string => typeof item === 'string');
  }
  return [typeof message === 'string' ? message : exception.message];
}
