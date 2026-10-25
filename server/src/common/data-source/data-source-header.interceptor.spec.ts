import type { CallHandler, ExecutionContext } from '@nestjs/common';
import { lastValueFrom, of } from 'rxjs';
import type { Mock } from 'vitest';
import { DataSourceHeaderInterceptor } from './data-source-header.interceptor.js';
import {
  ORGANIZER_DATASET_DATA_SOURCE,
  SourcedResponse,
  TBC_SANDBOX_DATA_SOURCE,
  type DataSource,
} from './data-source.js';

describe('DataSourceHeaderInterceptor', () => {
  const interceptor = new DataSourceHeaderInterceptor();
  let setHeader: Mock<(name: string, value: string) => void>;
  let context: ExecutionContext;

  beforeEach(() => {
    setHeader = vi.fn();
    context = {
      switchToHttp: () => ({ getResponse: () => ({ setHeader }) }),
    } as unknown as ExecutionContext;
  });

  function handlerReturning(result: unknown): CallHandler<unknown> {
    return { handle: () => of(result) };
  }

  it.each<DataSource>([TBC_SANDBOX_DATA_SOURCE, ORGANIZER_DATASET_DATA_SOURCE])(
    'sets X-Data-Source to %s and responds with the wrapped body',
    async (dataSource) => {
      const body = { consentStatus: 'valid' };

      const result = await lastValueFrom(
        interceptor.intercept(
          context,
          handlerReturning(new SourcedResponse(dataSource, body)),
        ),
      );

      expect(result).toBe(body);
      expect(setHeader).toHaveBeenCalledWith('X-Data-Source', dataSource);
    },
  );

  it('responds with an empty body when the wrapped body is undefined', async () => {
    const result = await lastValueFrom(
      interceptor.intercept(
        context,
        handlerReturning(
          new SourcedResponse(TBC_SANDBOX_DATA_SOURCE, undefined),
        ),
      ),
    );

    expect(result).toBeUndefined();
    expect(setHeader).toHaveBeenCalledWith('X-Data-Source', 'tbc-sandbox');
  });

  it('passes other results through without the header', async () => {
    const body = { status: 'ok' };

    const result = await lastValueFrom(
      interceptor.intercept(context, handlerReturning(body)),
    );

    expect(result).toBe(body);
    expect(setHeader).not.toHaveBeenCalled();
  });
});
