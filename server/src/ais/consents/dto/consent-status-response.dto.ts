import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString } from 'class-validator';
import {
  CONSENT_STATUSES,
  type ConsentStatus,
} from '../../shared/ais-formats.js';

export class ConsentStatusResponseDto {
  @ApiProperty({ enum: CONSENT_STATUSES })
  @IsIn(CONSENT_STATUSES)
  readonly consentStatus: ConsentStatus;

  @ApiPropertyOptional({ description: 'Text for the PSU from the bank.' })
  @IsOptional()
  @IsString()
  readonly psuMessage?: string;
}
