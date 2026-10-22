import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsArray, ValidateNested } from 'class-validator';
import { AccountDetailsDto } from './account-details.dto.js';

export class AccountListDto {
  @ApiProperty({
    type: () => [AccountDetailsDto],
    description: 'Accounts the consent grants.',
  })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => AccountDetailsDto)
  readonly accounts: AccountDetailsDto[];
}
