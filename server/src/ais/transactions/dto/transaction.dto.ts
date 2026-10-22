import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsArray,
  IsDefined,
  IsOptional,
  IsString,
  Matches,
  ValidateNested,
} from 'class-validator';
import {
  CURRENCY_CODE_PATTERN,
  ISO_DATE_PATTERN,
} from '../../shared/ais-formats.js';
import { AccountReferenceDto } from '../../shared/dto/account-reference.dto.js';
import { AmountDto } from '../../shared/dto/amount.dto.js';
import { BalanceDto } from '../../shared/dto/balance.dto.js';

export class ReportExchangeRateDto {
  @ApiProperty({ pattern: CURRENCY_CODE_PATTERN.source })
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly sourceCurrency: string;

  @ApiProperty({
    description:
      'Units of targetCurrency per unit of unitCurrency, as a decimal string.',
  })
  @IsString()
  readonly exchangeRate: string;

  @ApiProperty({ pattern: CURRENCY_CODE_PATTERN.source })
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly unitCurrency: string;

  @ApiProperty({ pattern: CURRENCY_CODE_PATTERN.source })
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly targetCurrency: string;

  @ApiProperty({ format: 'date' })
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly quotationDate: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  readonly contractIdentification?: string;
}

// Pending entries carry neither transactionId nor bookingDate (verified against the sandbox).
export class TransactionDto {
  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  readonly transactionId?: string;

  @ApiPropertyOptional({
    description: 'Reference of the entry in the account statement.',
  })
  @IsOptional()
  @IsString()
  readonly entryReference?: string;

  @ApiPropertyOptional({
    description: 'End-to-end reference shared by the legs of a transfer.',
  })
  @IsOptional()
  @IsString()
  readonly endToEndId?: string;

  @ApiPropertyOptional({ format: 'date' })
  @IsOptional()
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly bookingDate?: string;

  @ApiPropertyOptional({ format: 'date' })
  @IsOptional()
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly valueDate?: string;

  @ApiProperty({
    type: () => AmountDto,
    description: 'Signed amount: positive for credits, negative for debits.',
  })
  @IsDefined()
  @ValidateNested()
  @Type(() => AmountDto)
  readonly transactionAmount: AmountDto;

  @ApiPropertyOptional({ description: 'Payee of a debit.' })
  @IsOptional()
  @IsString()
  readonly creditorName?: string;

  @ApiPropertyOptional({ type: () => AccountReferenceDto })
  @IsOptional()
  @ValidateNested()
  @Type(() => AccountReferenceDto)
  readonly creditorAccount?: AccountReferenceDto;

  @ApiPropertyOptional({ description: 'Payer of a credit.' })
  @IsOptional()
  @IsString()
  readonly debtorName?: string;

  @ApiPropertyOptional({ type: () => AccountReferenceDto })
  @IsOptional()
  @ValidateNested()
  @Type(() => AccountReferenceDto)
  readonly debtorAccount?: AccountReferenceDto;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  readonly remittanceInformationUnstructured?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  readonly additionalInformation?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  readonly proprietaryBankTransactionCode?: string;

  @ApiPropertyOptional({ type: () => [ReportExchangeRateDto] })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ReportExchangeRateDto)
  readonly currencyExchange?: ReportExchangeRateDto[];

  @ApiPropertyOptional({ type: () => BalanceDto })
  @IsOptional()
  @ValidateNested()
  @Type(() => BalanceDto)
  readonly balanceAfterTransaction?: BalanceDto;
}
