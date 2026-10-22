import { ApiProperty } from '@nestjs/swagger';
import type { TppMessage, TppMessageCategory } from '../problem-details.js';

export class TppMessageDto implements TppMessage {
  @ApiProperty({ enum: ['ERROR', 'WARNING'] })
  readonly category: TppMessageCategory;

  @ApiProperty({ description: 'Machine-readable error code.' })
  readonly code: string;

  @ApiProperty({ description: 'Human-readable explanation of the error.' })
  readonly text: string;
}
