import { ApiProperty } from '@nestjs/swagger';
import { IsUUID } from 'class-validator';

export class ConsentIdParamDto {
  @ApiProperty({
    format: 'uuid',
    description: 'Identifier returned by POST /v1/consents.',
  })
  @IsUUID()
  readonly consentId: string;
}
