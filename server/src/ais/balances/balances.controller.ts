import { Controller, Get, HttpStatus, Param } from '@nestjs/common';
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
import { BalancesService } from './balances.service.js';
import { ReadAccountBalanceResponseDto } from './dto/read-account-balance-response.dto.js';

@ApiTags('AIS balances')
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
export class BalancesController {
  constructor(private readonly balancesService: BalancesService) {}

  @Get(':accountId/balances')
  @ApiOperation({ summary: 'Read the balances of one account' })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Account balances.',
    type: ReadAccountBalanceResponseDto,
  })
  readBalances(
    @Param() { accountId }: AccountIdParamDto,
    @ConsentIdHeader() consentId: string,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<ReadAccountBalanceResponseDto>> {
    return this.balancesService.readBalances(
      { ...context, consentId },
      accountId,
    );
  }
}
