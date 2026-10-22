import { AisProviderResolver } from './ais-provider-resolver.js';
import { PersonaBindingStore } from './persona-binding.store.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';

describe('AisProviderResolver', () => {
  let bindings: PersonaBindingStore;
  let resolver: AisProviderResolver;

  beforeEach(() => {
    bindings = new PersonaBindingStore();
    resolver = new AisProviderResolver(bindings);
  });

  it('serves a consent without persona binding from the TBC sandbox', () => {
    const dataSource = resolver.dataSourceFor(CONSENT_ID);

    expect(dataSource).toBe('tbc-sandbox');
  });

  it('serves a consent bound to a persona from the organizer dataset', () => {
    bindings.bind(CONSENT_ID, 'CUS-024');

    const dataSource = resolver.dataSourceFor(CONSENT_ID);

    expect(dataSource).toBe('organizer-dataset');
  });

  it('serves a consent from the TBC sandbox again once its binding is removed', () => {
    bindings.bind(CONSENT_ID, 'CUS-024');
    bindings.unbind(CONSENT_ID);

    const dataSource = resolver.dataSourceFor(CONSENT_ID);

    expect(dataSource).toBe('tbc-sandbox');
  });
});
