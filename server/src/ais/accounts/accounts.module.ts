import { Module } from '@nestjs/common';
import { AisProvidersModule } from '../providers/ais-providers.module.js';
import { AccountsController } from './accounts.controller.js';
import { AccountsService } from './accounts.service.js';

@Module({
  imports: [AisProvidersModule],
  controllers: [AccountsController],
  providers: [AccountsService],
})
export class AccountsModule {}
