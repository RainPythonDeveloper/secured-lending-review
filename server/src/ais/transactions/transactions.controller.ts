import { Controller, Get, HttpStatus, Param, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { SourcedResponse } from '../../common/data-source/data-source.js';
import {
  ConsentIdHeader,
  UpstreamContext,
} from '../../common/request-context/request-context.decorators.js';
import {
  ApiConsentIdHeader,
  ApiDataSourceResponseHeader,
  ApiProblemResponses,
  ApiPsuIpAddressHeader,
  ApiRequestIdHeader,
} from '../../common/swagger/api-gateway.decorators.js';
import type { UpstreamCallContext } from '../../tbc-client/upstream-call-context.js';
import { AccountIdParamDto } from '../shared/dto/account-id-param.dto.js';
import { TransactionListQueryDto } from './dto/transaction-list-query.dto.js';
import { TransactionsResponseDto } from './dto/transactions-response.dto.js';
import { TransactionsService } from './transactions.service.js';

@ApiTags('AIS transactions')
@ApiConsentIdHeader()
@ApiPsuIpAddressHeader()
@ApiRequestIdHeader()
@ApiProblemResponses(
  HttpStatus.BAD_REQUEST,
  HttpStatus.UNAUTHORIZED,
  HttpStatus.FORBIDDEN,
  HttpStatus.NOT_FOUND,
  HttpStatus.BAD_GATEWAY,
  HttpStatus.GATEWAY_TIMEOUT,
)
@Controller('v1/accounts')
export class TransactionsController {
  constructor(private readonly transactionsService: TransactionsService) {}

  @Get(':accountId/transactions')
  @ApiOperation({
    summary: 'Read the transactions of one account',
    description:
      'Signed string amounts: credits name the payer in debtorName, debits the payee in creditorName.',
  })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Transaction report of the account.',
    type: TransactionsResponseDto,
  })
  readTransactions(
    @Param() { accountId }: AccountIdParamDto,
    @Query() query: TransactionListQueryDto,
    @ConsentIdHeader() consentId: string,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<TransactionsResponseDto>> {
    return this.transactionsService.readTransactions(
      { ...context, consentId },
      accountId,
      query,
    );
  }
}
