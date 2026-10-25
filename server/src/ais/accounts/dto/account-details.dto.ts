import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsArray,
  IsOptional,
  IsString,
  Matches,
  ValidateNested,
} from 'class-validator';
import {
  BBAN_PATTERN,
  CURRENCY_CODE_PATTERN,
  IBAN_PATTERN,
} from '../../shared/ais-formats.js';
import { BalanceDto } from '../../shared/dto/balance.dto.js';
import { HrefDto } from '../../shared/dto/href.dto.js';

export class AccountLinksDto {
  @ApiPropertyOptional({
    type: () => HrefDto,
    description: 'The account resource.',
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => HrefDto)
  readonly account?: HrefDto;

  @ApiPropertyOptional({
    type: () => HrefDto,
    description: 'Balances of the account.',
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => HrefDto)
  readonly balances?: HrefDto;

  @ApiPropertyOptional({
    type: () => HrefDto,
    description: 'Transactions of the account.',
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => HrefDto)
  readonly transactions?: HrefDto;
}

export class AccountDetailsDto {
  @ApiProperty({
    description: 'Identifier of the account in the account paths.',
  })
  @IsString()
  readonly resourceId: string;

  @ApiPropertyOptional({ pattern: IBAN_PATTERN.source })
  @IsOptional()
  @IsString()
  @Matches(IBAN_PATTERN)
  readonly iban?: string;

  @ApiPropertyOptional({ pattern: BBAN_PATTERN.source })
  @IsOptional()
  @IsString()
  @Matches(BBAN_PATTERN)
  readonly bban?: string;

  @ApiProperty({
    description: 'ISO 4217 currency code.',
    pattern: CURRENCY_CODE_PATTERN.source,
  })
  @IsString()
  @Matches(CURRENCY_CODE_PATTERN)
  readonly currency: string;

  @ApiPropertyOptional({
    description: 'Name of the account given by the bank.',
  })
  @IsOptional()
  @IsString()
  readonly name?: string;

  @ApiPropertyOptional({ description: 'Name of the account given by the PSU.' })
  @IsOptional()
  @IsString()
  readonly displayName?: string;

  @ApiPropertyOptional({ description: 'Name of the account owner.' })
  @IsOptional()
  @IsString()
  readonly ownerName?: string;

  @ApiPropertyOptional({ description: 'Product name of the bank.' })
  @IsOptional()
  @IsString()
  readonly product?: string;

  @ApiPropertyOptional({
    description: 'ISO 20022 ExternalCashAccountType1Code, for example CACC.',
  })
  @IsOptional()
  @IsString()
  readonly cashAccountType?: string;

  @ApiPropertyOptional({ description: 'enabled, deleted or blocked.' })
  @IsOptional()
  @IsString()
  readonly status?: string;

  @ApiPropertyOptional({ description: 'BIC of the account servicing bank.' })
  @IsOptional()
  @IsString()
  readonly bic?: string;

  @ApiPropertyOptional({
    description: 'PRIV for private, ORGA for professional use.',
  })
  @IsOptional()
  @IsString()
  readonly usage?: string;

  @ApiPropertyOptional({
    type: () => [BalanceDto],
    description:
      'Present when withBalance=true and the consent grants the balances of the account.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => BalanceDto)
  readonly balances?: BalanceDto[];

  @ApiPropertyOptional({
    type: () => AccountLinksDto,
    description: 'Gateway links to the account resources.',
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => AccountLinksDto)
  readonly _links?: AccountLinksDto;
}
