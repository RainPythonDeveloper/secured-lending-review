import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { AccountsController } from './accounts.controller.js';
import { AccountsService } from './accounts.service.js';


@Module({
  imports: [HttpModule],
  controllers: [AccountsController],
  providers: [AccountsService],
})
export class AccountsModule {}