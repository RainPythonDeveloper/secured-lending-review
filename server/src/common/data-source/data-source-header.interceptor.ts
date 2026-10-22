import {
  Injectable,
  type CallHandler,
  type ExecutionContext,
  type NestInterceptor,
} from '@nestjs/common';
import type { Response } from 'express';
import { map, type Observable } from 'rxjs';
import { DATA_SOURCE_HEADER, SourcedResponse } from './data-source.js';

@Injectable()
export class DataSourceHeaderInterceptor implements NestInterceptor {
  intercept(
    context: ExecutionContext,
    next: CallHandler<unknown>,
  ): Observable<unknown> {
    const response = context.switchToHttp().getResponse<Response>();
    return next.handle().pipe(
      map((result) => {
        if (!(result instanceof SourcedResponse)) {
          return result;
        }
        response.setHeader(DATA_SOURCE_HEADER, result.dataSource);
        return result.body;
      }),
    );
  }
}
