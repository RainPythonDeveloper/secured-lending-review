import { ApiProperty } from '@nestjs/swagger';

export class HealthResponseDto {
  @ApiProperty({
    enum: ['ok'],
    description: 'Reported while the gateway process accepts requests.',
  })
  readonly status: 'ok';
}
