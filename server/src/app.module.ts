import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { createObserveModule } from '@nestjs/observe';
import { AppController } from './app.controller.js';
import { AppService } from './app.service.js';      // Путь к вашему сервису
import { AccountsController } from './account/accounts.controller.js';
import { AccountsService } from './account/accounts.service.js';

export const { ObserveModule, ObserveInstrument } = createObserveModule();

@Module({
  imports: [
    // Distributed tracing, auto-correlated logs, request/job metrics, error
    // telemetry, alarms, and more — out of the box. Sign up at https://observe.nestjs.com,
    // then run `npx @nestjs/observe link` to write your key pair into .env.
    ObserveModule.forRoot({
      appKey: process.env.OBSERVE_APP_KEY ?? 'YOUR_APP_KEY',
      appSecret: process.env.OBSERVE_APP_SECRET ?? 'YOUR_APP_SECRET',
      serviceId: 'server',
    }),
    HttpModule, // Обязательно для работы Axios-запросов к TBC Mock API
  ],
  controllers: [
    AppController,
    AccountsController, 
  ],
  providers: [
    AppService,
    AccountsService,  
  ],
})
export class AppModule {}