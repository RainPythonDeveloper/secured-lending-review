import { Module } from '@nestjs/common';
import { TbcClientModule } from '../tbc-client/tbc-client.module.js';
import { ConsentTokenStore } from './consent-token.store.js';
import { OAuthController } from './oauth.controller.js';
import { OAuthService } from './oauth.service.js';
import { PendingAuthorisationStore } from './pending-authorisation.store.js';

@Module({
  imports: [TbcClientModule],
  controllers: [OAuthController],
  providers: [OAuthService, PendingAuthorisationStore, ConsentTokenStore],
  exports: [OAuthService],
})
export class OAuthModule {}
