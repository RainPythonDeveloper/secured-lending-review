import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsDefined, ValidateNested } from 'class-validator';
import { AccountDetailsDto } from './account-details.dto.js';

export class AccountDetailsResponseDto {
  @ApiProperty({ type: () => AccountDetailsDto })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountDetailsDto)
  readonly account: AccountDetailsDto;
}
