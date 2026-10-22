import { ApiProperty } from '@nestjs/swagger';
import {
  CONSENT_STATUSES,
  type ConsentStatus,
} from '../../shared/ais-formats.js';
import { HrefDto } from '../../shared/dto/href.dto.js';

export class ConsentLinksDto {
  @ApiProperty({
    type: () => HrefDto,
    description:
      'Bank authorisation page (OAuth authorization code flow with PKCE). Open it in the PSU browser.',
  })
  readonly scaRedirect: HrefDto;

  @ApiProperty({ type: () => HrefDto, description: 'The consent resource.' })
  readonly self: HrefDto;

  @ApiProperty({ type: () => HrefDto, description: 'The consent status.' })
  readonly status: HrefDto;
}

export class CreateConsentResponseDto {
  @ApiProperty({ enum: CONSENT_STATUSES })
  readonly consentStatus: ConsentStatus;

  @ApiProperty({ format: 'uuid' })
  readonly consentId: string;

  @ApiProperty({ type: () => ConsentLinksDto })
  readonly _links: ConsentLinksDto;

  @ApiProperty({
    description:
      'Which synthetic data source serves the account data under this consent, and why.',
  })
  readonly psuMessage: string;
}
