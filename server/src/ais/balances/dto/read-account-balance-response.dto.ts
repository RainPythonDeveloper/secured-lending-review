import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsArray, IsDefined, ValidateNested } from 'class-validator';
import { AccountReferenceDto } from '../../shared/dto/account-reference.dto.js';
import { BalanceDto } from '../../shared/dto/balance.dto.js';

export class ReadAccountBalanceResponseDto {
  @ApiProperty({ type: () => AccountReferenceDto })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountReferenceDto)
  readonly account: AccountReferenceDto;

  @ApiProperty({ type: () => [BalanceDto] })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => BalanceDto)
  readonly balances: BalanceDto[];
}
