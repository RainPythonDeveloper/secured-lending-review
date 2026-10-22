import { HttpStatus, Injectable } from '@nestjs/common';
import { SourcedResponse } from '../../common/data-source/data-source.js';
import {
  PROBLEM_CODE,
  ProblemDetailsException,
  createProblem,
} from '../../common/problem-details/problem-details.js';
import type {
  AisReadContext,
  TransactionListQuery,
} from '../providers/ais-data-provider.js';
import { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import {
  DEFAULT_BOOKING_STATUS,
  type TransactionListQueryDto,
} from './dto/transaction-list-query.dto.js';
import type { TransactionsResponseDto } from './dto/transactions-response.dto.js';

@Injectable()
export class TransactionsService {
  constructor(private readonly providerResolver: AisProviderResolver) {}

  async readTransactions(
    context: AisReadContext,
    accountId: string,
    query: TransactionListQueryDto,
  ): Promise<SourcedResponse<TransactionsResponseDto>> {
    const transactionQuery = toTransactionListQuery(query);
    const provider = this.providerResolver.resolve(context.consentId);
    return new SourcedResponse(
      provider.dataSource,
      await provider.readTransactions(context, accountId, transactionQuery),
    );
  }
}

// ISO dates order chronologically as text.
function toTransactionListQuery({
  dateFrom,
  dateTo,
  bookingStatus,
}: TransactionListQueryDto): TransactionListQuery {
  if (dateFrom !== undefined && dateTo !== undefined && dateFrom > dateTo) {
    throw new ProblemDetailsException(
      createProblem({
        status: HttpStatus.BAD_REQUEST,
        code: PROBLEM_CODE.FORMAT_ERROR,
        detail: 'dateFrom must not be after dateTo',
      }),
    );
  }
  return {
    dateFrom,
    dateTo,
    bookingStatus: bookingStatus ?? DEFAULT_BOOKING_STATUS,
  };
}
