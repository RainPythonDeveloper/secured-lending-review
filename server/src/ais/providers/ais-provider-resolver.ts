import { Injectable } from '@nestjs/common';
import {
  ORGANIZER_DATASET_DATA_SOURCE,
  TBC_SANDBOX_DATA_SOURCE,
  type DataSource,
} from '../../common/data-source/data-source.js';
import { PersonaBindingStore } from './persona-binding.store.js';

@Injectable()
export class AisProviderResolver {
  constructor(private readonly bindings: PersonaBindingStore) {}

  dataSourceFor(consentId: string): DataSource {
    return this.bindings.findCustomerId(consentId) === undefined
      ? TBC_SANDBOX_DATA_SOURCE
      : ORGANIZER_DATASET_DATA_SOURCE;
  }
}
