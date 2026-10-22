import { isUUID } from 'class-validator';
import type { Request, Response } from 'express';
import { RequestIdMiddleware } from './request-id.middleware.js';

const CALLER_REQUEST_ID = '0f1e2d3c-4b5a-4968-8776-655443322110';

interface MiddlewareRun {
  responseHeaders: Map<string, string>;
  gatewayRequestId: string;
  hasCalledNext: boolean;
}

function runMiddleware(inboundRequestId: string | undefined): MiddlewareRun {
  const responseHeaders = new Map<string, string>();
  const request = {
    header: (name: string) =>
      name === 'X-Request-ID' ? inboundRequestId : undefined,
  };
  const response = {
    locals: { gatewayRequestId: '' },
    setHeader: (name: string, value: string) =>
      responseHeaders.set(name, value),
  };
  let hasCalledNext = false;
  new RequestIdMiddleware().use(
    request as unknown as Request,
    response as unknown as Response,
    () => {
      hasCalledNext = true;
    },
  );
  return {
    responseHeaders,
    gatewayRequestId: response.locals.gatewayRequestId,
    hasCalledNext,
  };
}

describe('RequestIdMiddleware', () => {
  it('keeps a UUID X-Request-ID sent by the caller', () => {
    const run = runMiddleware(CALLER_REQUEST_ID);

    expect(run.gatewayRequestId).toBe(CALLER_REQUEST_ID);
    expect(run.responseHeaders.get('X-Request-ID')).toBe(CALLER_REQUEST_ID);
  });

  it.each([
    ['missing', undefined],
    ['not a UUID', 'request-42'],
    ['empty', ''],
  ])(
    'generates a UUID v4 when the inbound X-Request-ID is %s',
    (_case, inboundRequestId) => {
      const run = runMiddleware(inboundRequestId);

      expect(isUUID(run.gatewayRequestId, 4)).toBe(true);
      expect(run.responseHeaders.get('X-Request-ID')).toBe(
        run.gatewayRequestId,
      );
    },
  );

  it('passes control to the next handler', () => {
    const run = runMiddleware(CALLER_REQUEST_ID);

    expect(run.hasCalledNext).toBe(true);
  });
});
