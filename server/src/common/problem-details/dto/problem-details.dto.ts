import { ApiProperty } from '@nestjs/swagger';
import { PROBLEM_TYPE_BLANK, type ProblemDetails } from '../problem-details.js';
import { TppMessageDto } from './tpp-message.dto.js';

export class ProblemDetailsDto implements ProblemDetails {
  @ApiProperty({ enum: [PROBLEM_TYPE_BLANK] })
  readonly type: string;

  @ApiProperty({ description: 'Same value as code.' })
  readonly title: string;

  @ApiProperty({ type: 'integer', description: 'HTTP status code.' })
  readonly status: number;

  @ApiProperty({
    description:
      'Machine-readable error code, for example FORMAT_ERROR, CONSENT_INVALID or UPSTREAM_TIMEOUT.',
  })
  readonly code: string;

  @ApiProperty({ description: 'Human-readable explanation of the error.' })
  readonly detail: string;

  @ApiProperty({ type: () => [TppMessageDto] })
  readonly tppMessages: TppMessageDto[];
}
