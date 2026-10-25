import { ApiProperty } from '@nestjs/swagger';

export const FINALISED_SCA_STATUS = 'finalised';

export class OAuthCallbackResponseDto {
  @ApiProperty({
    format: 'uuid',
    description: 'Consent that the PSU authorised at the bank.',
  })
  readonly consentId: string;

  @ApiProperty({
    enum: [FINALISED_SCA_STATUS],
    description:
      'Berlin Group SCA status. The tokens stay inside the gateway and are never returned.',
  })
  readonly scaStatus: typeof FINALISED_SCA_STATUS;
}
