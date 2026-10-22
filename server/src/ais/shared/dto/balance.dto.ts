import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsBoolean,
  IsDefined,
  IsIn,
  IsISO8601,
  IsOptional,
  IsString,
  Matches,
  ValidateNested,
} from 'class-validator';
import {
  BALANCE_TYPES,
  ISO_DATE_PATTERN,
  type BalanceType,
} from '../ais-formats.js';
import { AmountDto } from './amount.dto.js';

export class BalanceDto {
  @ApiProperty({ enum: BALANCE_TYPES })
  @IsIn(BALANCE_TYPES)
  readonly balanceType: BalanceType;

  @ApiProperty({ type: () => AmountDto })
  @IsDefined()
  @ValidateNested()
  @Type(() => AmountDto)
  readonly balanceAmount: AmountDto;

  @ApiPropertyOptional({
    description: 'Whether the balance includes the credit limit.',
  })
  @IsOptional()
  @IsBoolean()
  readonly creditLimitIncluded?: boolean;

  @ApiPropertyOptional({
    description: 'entryReference of the last transaction in the balance.',
  })
  @IsOptional()
  @IsString()
  readonly lastCommittedTransaction?: string;

  @ApiPropertyOptional({ format: 'date' })
  @IsOptional()
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly referenceDate?: string;

  @ApiPropertyOptional({ format: 'date-time' })
  @IsOptional()
  @IsISO8601()
  readonly lastChangeDateTime?: string;
}
