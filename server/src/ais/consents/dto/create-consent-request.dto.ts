import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsBoolean,
  IsDefined,
  IsInt,
  IsString,
  Matches,
  Max,
  Min,
  ValidateNested,
} from 'class-validator';
import { ISO_DATE_PATTERN } from '../../shared/ais-formats.js';
import { AccountAccessDto } from '../../shared/dto/account-access.dto.js';

// The specification caps the frequency at 4 unless agreed bilaterally; the sandbox rejects anything outside 1..4.
const MIN_FREQUENCY_PER_DAY = 1;
const MAX_FREQUENCY_PER_DAY = 4;

export class CreateConsentRequestDto {
  @ApiProperty({
    type: () => AccountAccessDto,
    description:
      'Requested access. Empty arrays ask for every account the PSU grants at the bank.',
    example: { accounts: [], balances: [], transactions: [] },
  })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountAccessDto)
  readonly access: AccountAccessDto;

  @ApiProperty({
    description: 'true for recurring access, false for a one-off access.',
    example: true,
  })
  @IsBoolean()
  readonly recurringIndicator: boolean;

  @ApiProperty({
    format: 'date',
    description: 'Last day on which the consent is valid (YYYY-MM-DD).',
    example: '2026-12-31',
  })
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly validUntil: string;

  @ApiProperty({
    type: 'integer',
    minimum: MIN_FREQUENCY_PER_DAY,
    maximum: MAX_FREQUENCY_PER_DAY,
    description: 'Maximum number of accesses per day without the PSU.',
    example: MAX_FREQUENCY_PER_DAY,
  })
  @IsInt()
  @Min(MIN_FREQUENCY_PER_DAY)
  @Max(MAX_FREQUENCY_PER_DAY)
  readonly frequencyPerDay: number;

  @ApiProperty({
    description: 'Whether the consent is combined with a payment initiation.',
    example: false,
  })
  @IsBoolean()
  readonly combinedServiceIndicator: boolean;
}
