import { Module } from '@nestjs/common';
import { FETCH } from './fetch.token.js';
import { RetryPolicy } from './retry-policy.js';
import { TbcClientService } from './tbc-client.service.js';
import { TbcHttpTransport } from './tbc-http-transport.js';

@Module({
  providers: [
    { provide: FETCH, useValue: globalThis.fetch },
    RetryPolicy,
    TbcHttpTransport,
    TbcClientService,
  ],
  exports: [TbcClientService],
})
export class TbcClientModule {}
