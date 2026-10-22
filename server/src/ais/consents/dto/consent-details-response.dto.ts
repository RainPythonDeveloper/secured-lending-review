import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsBoolean,
  IsDefined,
  IsIn,
  IsInt,
  IsString,
  Matches,
  ValidateNested,
} from 'class-validator';
import {
  CONSENT_STATUSES,
  ISO_DATE_PATTERN,
  type ConsentStatus,
} from '../../shared/ais-formats.js';
import { AccountAccessDto } from '../../shared/dto/account-access.dto.js';

export class ConsentDetailsResponseDto {
  @ApiProperty({
    type: () => AccountAccessDto,
    description: 'Access granted by the PSU at the bank.',
  })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountAccessDto)
  readonly access: AccountAccessDto;

  @ApiProperty()
  @IsBoolean()
  readonly recurringIndicator: boolean;

  @ApiProperty({ format: 'date' })
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly validUntil: string;

  @ApiProperty({ type: 'integer' })
  @IsInt()
  readonly frequencyPerDay: number;

  @ApiProperty({
    format: 'date',
    description: 'Date of the last action that changed the consent status.',
  })
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly lastActionDate: string;

  @ApiProperty({ enum: CONSENT_STATUSES })
  @IsIn(CONSENT_STATUSES)
  readonly consentStatus: ConsentStatus;
}
