import { personaRecords } from '../../../test/fixtures/organizer-dataset/persona-records.js';
import { loadSandboxFixture } from '../../../test/fixtures/load-fixture.js';
import {
  createFakeTbcClient,
  type FakeTbcClient,
} from '../../../test/support/fake-tbc-client.js';
import { FakeClock } from '../../../test/support/fake-runtime.js';
import { testGatewayConfig } from '../../../test/support/test-gateway-config.js';
import {
  ProblemDetailsException,
  createProblem,
} from '../../common/problem-details/problem-details.js';
import { ConsentTokenStore } from '../../oauth/consent-token.store.js';
import { OAuthService } from '../../oauth/oauth.service.js';
import { PendingAuthorisationStore } from '../../oauth/pending-authorisation.store.js';
import { OrganizerDataset } from '../../organizer-dataset/organizer-dataset.js';
import type { TbcClientService } from '../../tbc-client/tbc-client.service.js';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import { PersonaBindingStore } from '../providers/persona-binding.store.js';
import { ConsentsService } from './consents.service.js';
import type { CreateConsentRequestDto } from './dto/create-consent-request.dto.js';

const CONSENT_ID = '3f0c9a52-6d1e-4b7a-9c3e-1a2b3c4d5e6f';
const context: UpstreamCallContext = {
  gatewayRequestId: '6a0b7c1e-2f3d-4e5a-9b8c-7d6e5f4a3b2c',
  psuIpAddress: '203.0.113.7',
};
const consentRequest: CreateConsentRequestDto = {
  access: { accounts: [], balances: [], transactions: [] },
  recurringIndicator: true,
  validUntil: '2026-11-21',
  frequencyPerDay: 4,
  combinedServiceIndicator: false,
};

describe('ConsentsService', () => {
  let fakeTbcClient: FakeTbcClient;
  let oauthService: OAuthService;
  let bindings: PersonaBindingStore;
  let consentsService: ConsentsService;

  beforeEach(() => {
    fakeTbcClient = createFakeTbcClient();
    const tbcClient = fakeTbcClient as unknown as TbcClientService;
    const clock = new FakeClock(1_792_670_000_000);
    oauthService = new OAuthService(
      tbcClient,
      new PendingAuthorisationStore(clock, testGatewayConfig),
      new ConsentTokenStore(),
      clock,
      testGatewayConfig,
    );
    bindings = new PersonaBindingStore();
    consentsService = new ConsentsService(
      tbcClient,
      oauthService,
      OrganizerDataset.fromRecords(personaRecords),
      bindings,
      new AisProviderResolver(bindings),
    );
  });

  async function authoriseCreatedConsent(scaRedirectHref: string) {
    const state = new URL(scaRedirectHref).searchParams.get('state') ?? '';
    await oauthService.completeAuthorisation(
      { state, code: 'code_fixture-not-a-real-code' },
      context,
    );
  }

  describe('createConsent', () => {
    it('creates the consent at the bank with the request, PSU-ID and context', async () => {
      await consentsService.createConsent(consentRequest, 'CUS-024', context);

      expect(fakeTbcClient.createConsent).toHaveBeenCalledWith(
        consentRequest,
        'CUS-024',
        context,
      );
    });

    it('answers with the bank consent and gateway links', async () => {
      const created = await consentsService.createConsent(
        consentRequest,
        undefined,
        context,
      );

      expect(created.body).toMatchObject({
        consentStatus: 'received',
        consentId: CONSENT_ID,
        _links: {
          scaRedirect: {
            href: expect.stringContaining(
              `${testGatewayConfig.tbc.oauthAuthorizeUrl}?`,
            ),
          },
          self: { href: `/v1/consents/${CONSENT_ID}` },
          status: { href: `/v1/consents/${CONSENT_ID}/status` },
        },
      });
    });

    it('starts the bank authorisation for the created consent', async () => {
      const created = await consentsService.createConsent(
        consentRequest,
        undefined,
        context,
      );

      const scope = new URL(
        created.body._links.scaRedirect.href,
      ).searchParams.get('scope');
      expect(scope).toBe(`AIS:${CONSENT_ID}`);
    });

    it.each([
      [
        'a dataset customer',
        'CUS-024',
        'organizer-dataset',
        'Bound to organizer dataset persona CUS-024: account data under this consent comes from the synthetic organizer dataset. The bank consent screen shows the TBC sandbox demo customer.',
      ],
      [
        'an unknown PSU-ID',
        'CUS-999',
        'tbc-sandbox',
        'PSU-ID CUS-999 is not an organizer dataset customer: account data under this consent comes from the synthetic TBC mock sandbox.',
      ],
      [
        'no PSU-ID',
        undefined,
        'tbc-sandbox',
        'No PSU-ID given: account data under this consent comes from the synthetic TBC mock sandbox.',
      ],
    ])(
      'serves a consent for %s from the matching data source and says so',
      async (_case, psuId, expectedDataSource, expectedPsuMessage) => {
        const created = await consentsService.createConsent(
          consentRequest,
          psuId,
          context,
        );

        expect(created.dataSource).toBe(expectedDataSource);
        expect(created.body.psuMessage).toBe(expectedPsuMessage);
      },
    );

    it('binds the consent to the dataset customer named by PSU-ID', async () => {
      await consentsService.createConsent(consentRequest, 'CUS-024', context);

      expect(bindings.findCustomerId(CONSENT_ID)).toBe('CUS-024');
    });

    it('binds nothing for a PSU-ID that is not in the dataset', async () => {
      await consentsService.createConsent(consentRequest, 'CUS-999', context);

      expect(bindings.findCustomerId(CONSENT_ID)).toBeUndefined();
    });

    it('rejects a bank answer without a consent id as a contract violation', async () => {
      fakeTbcClient.createConsent.mockResolvedValue({
        consentStatus: 'received',
      });

      const creating = consentsService.createConsent(
        consentRequest,
        'CUS-024',
        context,
      );

      await expect(creating).rejects.toMatchObject({
        problem: { status: 502, code: 'UPSTREAM_CONTRACT_VIOLATION' },
      });
      expect(bindings.findCustomerId(CONSENT_ID)).toBeUndefined();
    });
  });

  describe('getConsent', () => {
    it('returns the bank consent without the upstream links', async () => {
      const consent = await consentsService.getConsent(CONSENT_ID, context);

      expect(fakeTbcClient.getConsent).toHaveBeenCalledWith(
        CONSENT_ID,
        context,
      );
      expect(consent.body).toEqual({
        ...(loadSandboxFixture('consent-details.200.json') as object),
        _links: undefined,
      });
      expect(consent.body).not.toHaveProperty('_links');
    });

    it('reports the data source of a persona-bound consent', async () => {
      bindings.bind(CONSENT_ID, 'CUS-024');

      const consent = await consentsService.getConsent(CONSENT_ID, context);

      expect(consent.dataSource).toBe('organizer-dataset');
    });

    it('rejects a bank consent with an unknown status as a contract violation', async () => {
      fakeTbcClient.getConsent.mockResolvedValue({
        ...(loadSandboxFixture('consent-details.200.json') as object),
        consentStatus: 'approved',
      });

      const reading = consentsService.getConsent(CONSENT_ID, context);

      await expect(reading).rejects.toMatchObject({
        problem: { status: 502, code: 'UPSTREAM_CONTRACT_VIOLATION' },
      });
    });
  });

  describe('getConsentStatus', () => {
    it('returns the bank consent status', async () => {
      fakeTbcClient.getConsentStatus.mockResolvedValue(
        loadSandboxFixture('consent-status.terminated-by-tpp.200.json'),
      );

      const consentStatus = await consentsService.getConsentStatus(
        CONSENT_ID,
        context,
      );

      expect(consentStatus.dataSource).toBe('tbc-sandbox');
      expect(consentStatus.body).toEqual({
        consentStatus: 'terminatedByTpp',
      });
    });
  });

  describe('deleteConsent', () => {
    it('terminates the consent at the bank', async () => {
      await consentsService.deleteConsent(CONSENT_ID, context);

      expect(fakeTbcClient.deleteConsent).toHaveBeenCalledWith(
        CONSENT_ID,
        context,
      );
    });

    it('forgets the tokens and the persona binding of the consent', async () => {
      const created = await consentsService.createConsent(
        consentRequest,
        'CUS-024',
        context,
      );
      await authoriseCreatedConsent(created.body._links.scaRedirect.href);

      await consentsService.deleteConsent(CONSENT_ID, context);

      expect(oauthService.hasAuthorisedTokens(CONSENT_ID)).toBe(false);
      expect(bindings.findCustomerId(CONSENT_ID)).toBeUndefined();
    });

    it('reports the data source the consent had before deletion', async () => {
      bindings.bind(CONSENT_ID, 'CUS-024');

      const deleted = await consentsService.deleteConsent(CONSENT_ID, context);

      expect(deleted).toEqual({
        dataSource: 'organizer-dataset',
        body: undefined,
      });
    });

    it('keeps the persona binding when the bank fails to delete the consent', async () => {
      const unavailable = new ProblemDetailsException(
        createProblem({
          status: 502,
          code: 'SERVICE_UNAVAILABLE',
          detail: 'Injected synthetic failure (after 1 attempt)',
        }),
      );
      fakeTbcClient.deleteConsent.mockRejectedValue(unavailable);
      bindings.bind(CONSENT_ID, 'CUS-024');

      const deleting = consentsService.deleteConsent(CONSENT_ID, context);

      await expect(deleting).rejects.toBe(unavailable);
      expect(bindings.findCustomerId(CONSENT_ID)).toBe('CUS-024');
    });
  });
});
