import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString, Matches } from 'class-validator';
import {
  BOOKING_STATUSES,
  ISO_DATE_PATTERN,
  type BookingStatus,
} from '../../shared/ais-formats.js';

// The sandbox answers with booked entries only when bookingStatus is absent.
export const DEFAULT_BOOKING_STATUS: BookingStatus = 'booked';

export class TransactionListQueryDto {
  @ApiPropertyOptional({
    format: 'date',
    description: 'First booking date to include (YYYY-MM-DD).',
  })
  @IsOptional()
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly dateFrom?: string;

  @ApiPropertyOptional({
    format: 'date',
    description:
      'Last booking date to include (YYYY-MM-DD), not before dateFrom.',
  })
  @IsOptional()
  @IsString()
  @Matches(ISO_DATE_PATTERN)
  readonly dateTo?: string;

  @ApiPropertyOptional({
    enum: BOOKING_STATUSES,
    default: DEFAULT_BOOKING_STATUS,
  })
  @IsOptional()
  @IsIn(BOOKING_STATUSES)
  readonly bookingStatus?: BookingStatus;
}
