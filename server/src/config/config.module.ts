import { Global, Module } from '@nestjs/common';
import { GatewayConfig } from './gateway-config.js';
import { loadGatewayConfig } from './load-gateway-config.js';

@Global()
@Module({
  providers: [
    {
      provide: GatewayConfig,
      useFactory: (): GatewayConfig => loadGatewayConfig(process.env),
    },
  ],
  exports: [GatewayConfig],
})
export class ConfigModule {}
