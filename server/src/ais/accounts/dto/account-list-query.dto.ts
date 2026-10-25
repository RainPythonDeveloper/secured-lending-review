import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsIn, IsOptional } from 'class-validator';

const WITH_BALANCE_VALUES = ['true', 'false'] as const;

type WithBalanceValue = (typeof WITH_BALANCE_VALUES)[number];

export class AccountListQueryDto {
  @ApiPropertyOptional({
    enum: WITH_BALANCE_VALUES,
    description:
      'true adds the balances of every account whose balances the consent grants.',
  })
  @IsOptional()
  @IsIn(WITH_BALANCE_VALUES)
  readonly withBalance?: WithBalanceValue;
}
