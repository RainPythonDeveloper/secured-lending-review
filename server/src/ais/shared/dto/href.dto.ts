import { ApiProperty } from '@nestjs/swagger';
import { IsString } from 'class-validator';

export class HrefDto {
  @ApiProperty({ description: 'Link to a resource.' })
  @IsString()
  readonly href: string;
}
