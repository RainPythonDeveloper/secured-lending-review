import { Module } from '@nestjs/common';
import { AisProviderResolver } from './ais-provider-resolver.js';
import { PersonaBindingStore } from './persona-binding.store.js';

@Module({
  providers: [PersonaBindingStore, AisProviderResolver],
  exports: [PersonaBindingStore, AisProviderResolver],
})
export class AisProvidersModule {}
