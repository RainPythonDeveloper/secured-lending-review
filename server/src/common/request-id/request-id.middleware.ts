import { randomUUID } from 'node:crypto';
import { Injectable, type NestMiddleware } from '@nestjs/common';
import { isUUID } from 'class-validator';
import type { NextFunction, Request, Response } from 'express';
import { OPEN_BANKING_HEADER } from '../open-banking-headers.js';

// Express types response locals only through its global namespace.
declare global {
  namespace Express {
    interface Locals {
      gatewayRequestId: string;
    }
  }
}

@Injectable()
export class RequestIdMiddleware implements NestMiddleware {
  use(request: Request, response: Response, next: NextFunction): void {
    const gatewayRequestId = resolveGatewayRequestId(
      request.header(OPEN_BANKING_HEADER.REQUEST_ID),
    );
    response.locals.gatewayRequestId = gatewayRequestId;
    response.setHeader(OPEN_BANKING_HEADER.REQUEST_ID, gatewayRequestId);
    next();
  }
}

function resolveGatewayRequestId(inboundRequestId: string | undefined): string {
  return inboundRequestId !== undefined && isUUID(inboundRequestId)
    ? inboundRequestId
    : randomUUID();
}
