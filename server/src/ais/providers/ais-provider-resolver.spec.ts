import { personaRecords } from '../../../test/fixtures/organizer-dataset/persona-records.js';
import { createFakeTbcClient } from '../../../test/support/fake-tbc-client.js';
import { createOAuthServiceWithTokens } from '../../../test/support/oauth-service-with-tokens.js';
import { OrganizerDataset } from '../../organizer-dataset/organizer-dataset.js';
import type { TbcClientService } from '../../tbc-client/tbc-client.service.js';
import { AisProviderResolver } from './ais-provider-resolver.js';
import { DatasetAisProvider } from './dataset/dataset-ais-provider.js';
import { PersonaBindingStore } from './persona-binding.store.js';
import { SandboxAisProvider } from './sandbox/sandbox-ais-provider.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';

describe('AisProviderResolver', () => {
  let bindings: PersonaBindingStore;
  let sandboxProvider: SandboxAisProvider;
  let datasetProvider: DatasetAisProvider;
  let resolver: AisProviderResolver;

  beforeEach(() => {
    const fakeTbcClient = createFakeTbcClient();
    const tbcClient = fakeTbcClient as unknown as TbcClientService;
    const oauthService = createOAuthServiceWithTokens(fakeTbcClient, []);
    bindings = new PersonaBindingStore();
    sandboxProvider = new SandboxAisProvider(tbcClient, oauthService);
    datasetProvider = new DatasetAisProvider(
      tbcClient,
      oauthService,
      OrganizerDataset.fromRecords(personaRecords),
      bindings,
    );
    resolver = new AisProviderResolver(
      bindings,
      sandboxProvider,
      datasetProvider,
    );
  });

  describe('resolve', () => {
    it('serves a consent without persona binding from the TBC sandbox provider', () => {
      const provider = resolver.resolve(CONSENT_ID);

      expect(provider).toBe(sandboxProvider);
    });

    it('serves a consent bound to a persona from the organizer dataset provider', () => {
      bindings.bind(CONSENT_ID, 'CUS-024');

      const provider = resolver.resolve(CONSENT_ID);

      expect(provider).toBe(datasetProvider);
    });

    it('serves a consent from the TBC sandbox provider again once its binding is removed', () => {
      bindings.bind(CONSENT_ID, 'CUS-024');
      bindings.unbind(CONSENT_ID);

      const provider = resolver.resolve(CONSENT_ID);

      expect(provider).toBe(sandboxProvider);
    });
  });

  describe('dataSourceFor', () => {
    it('reports the TBC sandbox for a consent without persona binding', () => {
      const dataSource = resolver.dataSourceFor(CONSENT_ID);

      expect(dataSource).toBe('tbc-sandbox');
    });

    it('reports the organizer dataset for a consent bound to a persona', () => {
      bindings.bind(CONSENT_ID, 'CUS-024');

      const dataSource = resolver.dataSourceFor(CONSENT_ID);

      expect(dataSource).toBe('organizer-dataset');
    });
  });
});
