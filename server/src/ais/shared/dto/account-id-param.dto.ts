import { ApiProperty } from '@nestjs/swagger';
import { IsString, Matches } from 'class-validator';
import { ACCOUNT_ID_PATTERN } from '../ais-formats.js';

export class AccountIdParamDto {
  @ApiProperty({
    description: 'resourceId of the account as listed by GET /v1/accounts.',
    pattern: ACCOUNT_ID_PATTERN.source,
  })
  @IsString()
  @Matches(ACCOUNT_ID_PATTERN)
  readonly accountId: string;
}
