import { Module } from '@nestjs/common';
import { OAuthModule } from '../../oauth/oauth.module.js';
import { OrganizerDatasetModule } from '../../organizer-dataset/organizer-dataset.module.js';
import { TbcClientModule } from '../../tbc-client/tbc-client.module.js';
import { AisProvidersModule } from '../providers/ais-providers.module.js';
import { ConsentsController } from './consents.controller.js';
import { ConsentsService } from './consents.service.js';

@Module({
  imports: [
    TbcClientModule,
    OAuthModule,
    OrganizerDatasetModule,
    AisProvidersModule,
  ],
  controllers: [ConsentsController],
  providers: [ConsentsService],
})
export class ConsentsModule {}
