import { ApiPropertyOptional } from '@nestjs/swagger';
import {
  IsIn,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
} from 'class-validator';
import {
  BBAN_PATTERN,
  CASH_ACCOUNT_TYPES,
  CURRENCY_CODE_PATTERN,
  IBAN_PATTERN,
  MASKED_PAN_MAX_LENGTH,
  type CashAccountType,
} from '../ais-formats.js';

export class AccountReferenceDto {
  @ApiPropertyOptional({
    description: 'IBAN of the account.',
    pattern: IBAN_PATTERN.source,
  })
  @IsOptional()
  @IsString()
  @Matches(IBAN_PATTERN)
  readonly iban?: string;

  @ApiPropertyOptional({
    description: 'Basic Bank Account Number.',
    pattern: BBAN_PATTERN.source,
  })
  @IsOptional()
  @IsString()
  @Matches(BBAN_PATTERN)
  readonly bban?: string;

  @ApiPropertyOptional({
    description: 'Masked primary account number of a card.',
    maxLength: MASKED_PAN_MAX_LENGTH,
  })
  @IsOptional()
  @IsString()
  @MaxLength(MASKED_PAN_MAX_LENGTH)
  readonly maskedPan?: string;

  @ApiPropertyOptional({
    description: 'ISO 4217 currency code.',
    pattern: CURRENCY_CODE_PATTERN.source,
  })
  @IsOptional()
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly currency?: string;

  @ApiPropertyOptional({
    enum: CASH_ACCOUNT_TYPES,
    description: 'ISO 20022 ExternalCashAccountType1Code.',
  })
  @IsOptional()
  @IsIn(CASH_ACCOUNT_TYPES)
  readonly cashAccountType?: CashAccountType;
}
