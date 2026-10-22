import { createParamDecorator, type ExecutionContext } from '@nestjs/common';
import type { Request, Response } from 'express';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import {
  readConsentIdHeader,
  readPsuIdHeader,
  readPsuIpAddress,
} from './request-headers.js';

// ValidationPipe skips custom parameter decorators, so headers are validated here.
export const ConsentIdHeader = createParamDecorator(
  (_data: unknown, context: ExecutionContext): string =>
    readConsentIdHeader(context.switchToHttp().getRequest<Request>().headers),
);

export const PsuIdHeader = createParamDecorator(
  (_data: unknown, context: ExecutionContext): string | undefined =>
    readPsuIdHeader(context.switchToHttp().getRequest<Request>().headers),
);

export const UpstreamContext = createParamDecorator(
  (_data: unknown, context: ExecutionContext): UpstreamCallContext => {
    const http = context.switchToHttp();
    const request = http.getRequest<Request>();
    return {
      gatewayRequestId: http.getResponse<Response>().locals.gatewayRequestId,
      psuIpAddress: readPsuIpAddress(request.headers, request.ip),
    };
  },
);
