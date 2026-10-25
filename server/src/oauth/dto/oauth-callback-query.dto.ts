import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsNotEmpty, IsOptional, IsString, IsUUID } from 'class-validator';

// OAuth 2.0 parameter names (RFC 6749 §4.1.2) are kept verbatim.
export class OAuthCallbackQueryDto {
  @ApiProperty({
    format: 'uuid',
    description:
      'State issued by the gateway when the authorisation started. Valid once.',
  })
  @IsUUID()
  readonly state: string;

  @ApiPropertyOptional({
    description:
      'Authorisation code issued by the bank after the PSU approved the consent.',
  })
  @IsOptional()
  @IsString()
  @IsNotEmpty()
  readonly code?: string;

  @ApiPropertyOptional({
    description:
      'OAuth error code reported by the bank (RFC 6749 section 4.1.2.1), for example when the PSU rejected the consent.',
  })
  @IsOptional()
  @IsString()
  @IsNotEmpty()
  readonly error?: string;

  @ApiPropertyOptional({
    description: 'Human-readable explanation of the OAuth error.',
  })
  @IsOptional()
  @IsString()
  readonly error_description?: string;

  @ApiPropertyOptional({
    description: 'Page describing the OAuth error.',
  })
  @IsOptional()
  @IsString()
  readonly error_uri?: string;
}
