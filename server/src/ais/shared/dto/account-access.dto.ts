import { ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsArray, IsIn, IsOptional, ValidateNested } from 'class-validator';
import {
  AVAILABLE_ACCOUNTS_VALUES,
  type AvailableAccountsValue,
} from '../ais-formats.js';
import { AccountReferenceDto } from './account-reference.dto.js';

export class AccountAccessDto {
  @ApiPropertyOptional({
    type: () => [AccountReferenceDto],
    description:
      'Accounts whose details are requested. An empty array asks for every account the PSU grants.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => AccountReferenceDto)
  readonly accounts?: AccountReferenceDto[];

  @ApiPropertyOptional({
    type: () => [AccountReferenceDto],
    description:
      'Accounts whose balances are requested. An empty array asks for the balances of every granted account.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => AccountReferenceDto)
  readonly balances?: AccountReferenceDto[];

  @ApiPropertyOptional({
    type: () => [AccountReferenceDto],
    description:
      'Accounts whose transactions are requested. An empty array asks for the transactions of every granted account.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => AccountReferenceDto)
  readonly transactions?: AccountReferenceDto[];

  @ApiPropertyOptional({
    enum: AVAILABLE_ACCOUNTS_VALUES,
    description: 'Asks for the list of available accounts only.',
  })
  @IsOptional()
  @IsIn(AVAILABLE_ACCOUNTS_VALUES)
  readonly availableAccounts?: AvailableAccountsValue;

  @ApiPropertyOptional({
    enum: AVAILABLE_ACCOUNTS_VALUES,
    description:
      'Asks for the list of available accounts together with their balances.',
  })
  @IsOptional()
  @IsIn(AVAILABLE_ACCOUNTS_VALUES)
  readonly availableAccountsWithBalance?: AvailableAccountsValue;
}
