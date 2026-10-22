import { Module } from '@nestjs/common';
import { OAuthModule } from '../../oauth/oauth.module.js';
import { OrganizerDatasetModule } from '../../organizer-dataset/organizer-dataset.module.js';
import { TbcClientModule } from '../../tbc-client/tbc-client.module.js';
import { AisProviderResolver } from './ais-provider-resolver.js';
import { DatasetAisProvider } from './dataset/dataset-ais-provider.js';
import { PersonaBindingStore } from './persona-binding.store.js';
import { SandboxAisProvider } from './sandbox/sandbox-ais-provider.js';

@Module({
  imports: [TbcClientModule, OAuthModule, OrganizerDatasetModule],
  providers: [
    PersonaBindingStore,
    SandboxAisProvider,
    DatasetAisProvider,
    AisProviderResolver,
  ],
  exports: [PersonaBindingStore, AisProviderResolver],
})
export class AisProvidersModule {}
