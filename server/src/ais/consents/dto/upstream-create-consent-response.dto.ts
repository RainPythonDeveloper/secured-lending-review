import { IsIn, IsUUID } from 'class-validator';
import {
  CONSENT_STATUSES,
  type ConsentStatus,
} from '../../shared/ais-formats.js';

// Only the fields the gateway uses; the sandbox _links point at upstream paths callers cannot reach.
export class UpstreamCreateConsentResponseDto {
  @IsUUID()
  readonly consentId: string;

  @IsIn(CONSENT_STATUSES)
  readonly consentStatus: ConsentStatus;
}
