import { Injectable } from '@nestjs/common';
import { SourcedResponse } from '../../common/data-source/data-source.js';
import { OAuthService } from '../../oauth/oauth.service.js';
import { OrganizerDataset } from '../../organizer-dataset/organizer-dataset.js';
import { TbcClientService } from '../../tbc-client/tbc-client.service.js';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import { parseUpstreamPayload } from '../../tbc-client/upstream-payload.js';
import { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import { PersonaBindingStore } from '../providers/persona-binding.store.js';
import { ConsentDetailsResponseDto } from './dto/consent-details-response.dto.js';
import { ConsentStatusResponseDto } from './dto/consent-status-response.dto.js';
import type { CreateConsentRequestDto } from './dto/create-consent-request.dto.js';
import type {
  ConsentLinksDto,
  CreateConsentResponseDto,
} from './dto/create-consent-response.dto.js';
import { UpstreamCreateConsentResponseDto } from './dto/upstream-create-consent-response.dto.js';

const CONSENTS_PATH = '/v1/consents';

@Injectable()
export class ConsentsService {
  constructor(
    private readonly tbcClient: TbcClientService,
    private readonly oauthService: OAuthService,
    private readonly dataset: OrganizerDataset,
    private readonly bindings: PersonaBindingStore,
    private readonly providerResolver: AisProviderResolver,
  ) {}

  // The consent always lives at the bank; PSU-ID only decides which synthetic data it serves.
  async createConsent(
    request: CreateConsentRequestDto,
    psuId: string | undefined,
    context: UpstreamCallContext,
  ): Promise<SourcedResponse<CreateConsentResponseDto>> {
    const { consentId, consentStatus } = parseUpstreamPayload(
      UpstreamCreateConsentResponseDto,
      await this.tbcClient.createConsent(request, psuId, context),
      'createConsent',
    );
    const scaRedirectHref = this.oauthService.startAuthorisation(consentId);
    const personaCustomerId =
      psuId !== undefined && this.dataset.hasCustomer(psuId)
        ? psuId
        : undefined;
    if (personaCustomerId !== undefined) {
      this.bindings.bind(consentId, personaCustomerId);
    }
    return new SourcedResponse(this.providerResolver.dataSourceFor(consentId), {
      consentStatus,
      consentId,
      _links: buildConsentLinks(consentId, scaRedirectHref),
      psuMessage: describeDataSourceChoice(psuId, personaCustomerId),
    });
  }

  async getConsent(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<SourcedResponse<ConsentDetailsResponseDto>> {
    const consent = parseUpstreamPayload(
      ConsentDetailsResponseDto,
      await this.tbcClient.getConsent(consentId, context),
      'getConsent',
    );
    return new SourcedResponse(
      this.providerResolver.dataSourceFor(consentId),
      consent,
    );
  }

  async getConsentStatus(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<SourcedResponse<ConsentStatusResponseDto>> {
    const consentStatus = parseUpstreamPayload(
      ConsentStatusResponseDto,
      await this.tbcClient.getConsentStatus(consentId, context),
      'getConsentStatus',
    );
    return new SourcedResponse(
      this.providerResolver.dataSourceFor(consentId),
      consentStatus,
    );
  }

  async deleteConsent(
    consentId: string,
    context: UpstreamCallContext,
  ): Promise<SourcedResponse<undefined>> {
    const dataSourceBeforeDeletion =
      this.providerResolver.dataSourceFor(consentId);
    await this.tbcClient.deleteConsent(consentId, context);
    this.oauthService.forgetConsent(consentId);
    this.bindings.unbind(consentId);
    return new SourcedResponse(dataSourceBeforeDeletion, undefined);
  }
}

function buildConsentLinks(
  consentId: string,
  scaRedirectHref: string,
): ConsentLinksDto {
  const consentPath = `${CONSENTS_PATH}/${consentId}`;
  return {
    scaRedirect: { href: scaRedirectHref },
    self: { href: consentPath },
    status: { href: `${consentPath}/status` },
  };
}

function describeDataSourceChoice(
  psuId: string | undefined,
  personaCustomerId: string | undefined,
): string {
  if (personaCustomerId !== undefined) {
    return (
      `Bound to organizer dataset persona ${personaCustomerId}: account data under this consent comes from the ` +
      'synthetic organizer dataset. The bank consent screen shows the TBC sandbox demo customer.'
    );
  }
  if (psuId !== undefined) {
    return (
      `PSU-ID ${psuId} is not an organizer dataset customer: account data under this consent comes ` +
      'from the synthetic TBC mock sandbox.'
    );
  }
  return 'No PSU-ID given: account data under this consent comes from the synthetic TBC mock sandbox.';
}
