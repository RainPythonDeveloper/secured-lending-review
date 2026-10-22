import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import {
  IsArray,
  IsDefined,
  IsOptional,
  ValidateNested,
} from 'class-validator';
import { AccountReferenceDto } from '../../shared/dto/account-reference.dto.js';
import { HrefDto } from '../../shared/dto/href.dto.js';
import { TransactionDto } from './transaction.dto.js';

export class TransactionLinksDto {
  @ApiProperty({ type: () => HrefDto, description: 'The account resource.' })
  @IsDefined()
  @ValidateNested()
  @Type(() => HrefDto)
  readonly account: HrefDto;
}

export class AccountReportDto {
  @ApiPropertyOptional({
    type: () => [TransactionDto],
    description: 'Present for bookingStatus booked or both.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => TransactionDto)
  readonly booked?: TransactionDto[];

  @ApiPropertyOptional({
    type: () => [TransactionDto],
    description: 'Present for bookingStatus pending or both.',
  })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => TransactionDto)
  readonly pending?: TransactionDto[];

  @ApiPropertyOptional({
    type: () => TransactionLinksDto,
    description: 'Gateway links of the report.',
  })
  @IsOptional()
  @ValidateNested()
  @Type(() => TransactionLinksDto)
  readonly _links?: TransactionLinksDto;
}

export class TransactionsResponseDto {
  @ApiProperty({ type: () => AccountReferenceDto })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountReferenceDto)
  readonly account: AccountReferenceDto;

  @ApiProperty({ type: () => AccountReportDto })
  @IsDefined()
  @ValidateNested()
  @Type(() => AccountReportDto)
  readonly transactions: AccountReportDto;
}
