import { Module, ValidationPipe } from '@nestjs/common';
import { APP_FILTER, APP_INTERCEPTOR, APP_PIPE } from '@nestjs/core';
import { ConsentsModule } from './ais/consents/consents.module.js';
import { CommonModule } from './common/common.module.js';
import { DataSourceHeaderInterceptor } from './common/data-source/data-source-header.interceptor.js';
import { ProblemDetailsFilter } from './common/problem-details/problem-details.filter.js';
import { ConfigModule } from './config/config.module.js';
import { HealthModule } from './health/health.module.js';
import { OAuthModule } from './oauth/oauth.module.js';
import { OrganizerDatasetModule } from './organizer-dataset/organizer-dataset.module.js';
import { TbcClientModule } from './tbc-client/tbc-client.module.js';

@Module({
  imports: [
    ConfigModule,
    CommonModule,
    HealthModule,
    TbcClientModule,
    OAuthModule,
    OrganizerDatasetModule,
    ConsentsModule,
  ],
  providers: [
    {
      provide: APP_PIPE,
      useValue: new ValidationPipe({
        whitelist: true,
        forbidNonWhitelisted: true,
        transform: true,
      }),
    },
    { provide: APP_FILTER, useClass: ProblemDetailsFilter },
    { provide: APP_INTERCEPTOR, useClass: DataSourceHeaderInterceptor },
  ],
})
export class AppModule {}
