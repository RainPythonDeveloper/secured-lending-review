import { Module } from '@nestjs/common';
import { AisProvidersModule } from '../providers/ais-providers.module.js';
import { BalancesController } from './balances.controller.js';
import { BalancesService } from './balances.service.js';

@Module({
  imports: [AisProvidersModule],
  controllers: [BalancesController],
  providers: [BalancesService],
})
export class BalancesModule {}
