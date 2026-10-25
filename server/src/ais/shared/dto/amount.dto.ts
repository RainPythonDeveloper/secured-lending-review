import { ApiProperty } from '@nestjs/swagger';
import { IsString, Matches } from 'class-validator';
import { AMOUNT_PATTERN, CURRENCY_CODE_PATTERN } from '../ais-formats.js';

export class AmountDto {
  @ApiProperty({
    description: 'ISO 4217 currency code.',
    pattern: CURRENCY_CODE_PATTERN.source,
    example: 'GEL',
  })
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly currency: string;

  @ApiProperty({
    description:
      'Amount as a decimal string, never a JSON number. Negative for debits.',
    pattern: AMOUNT_PATTERN.source,
    example: '3247.50',
  })
  @IsString()
  @Matches(AMOUNT_PATTERN)
  readonly amount: string;
}
