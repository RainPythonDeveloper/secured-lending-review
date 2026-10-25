import { Injectable } from '@nestjs/common';
import type { DataSource } from '../../common/data-source/data-source.js';
import type { AisDataProvider } from './ais-data-provider.js';
import { DatasetAisProvider } from './dataset/dataset-ais-provider.js';
import { PersonaBindingStore } from './persona-binding.store.js';
import { SandboxAisProvider } from './sandbox/sandbox-ais-provider.js';

@Injectable()
export class AisProviderResolver {
  constructor(
    private readonly bindings: PersonaBindingStore,
    private readonly sandboxProvider: SandboxAisProvider,
    private readonly datasetProvider: DatasetAisProvider,
  ) {}

  resolve(consentId: string): AisDataProvider {
    return this.bindings.findCustomerId(consentId) === undefined
      ? this.sandboxProvider
      : this.datasetProvider;
  }

  dataSourceFor(consentId: string): DataSource {
    return this.resolve(consentId).dataSource;
  }
}
