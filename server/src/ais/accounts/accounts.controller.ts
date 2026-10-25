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
import { AccountsService } from './accounts.service.js';
import { AccountDetailsResponseDto } from './dto/account-details-response.dto.js';
import { AccountListQueryDto } from './dto/account-list-query.dto.js';
import { AccountListDto } from './dto/account-list.dto.js';

@ApiTags('AIS accounts')
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
export class AccountsController {
  constructor(private readonly accountsService: AccountsService) {}

  @Get()
  @ApiOperation({ summary: 'List the accounts the consent grants' })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description:
      'Accounts with links to their details, balances and transactions.',
    type: AccountListDto,
  })
  listAccounts(
    @Query() { withBalance }: AccountListQueryDto,
    @ConsentIdHeader() consentId: string,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<AccountListDto>> {
    return this.accountsService.listAccounts(
      { ...context, consentId },
      withBalance === 'true',
    );
  }

  @Get(':accountId')
  @ApiOperation({ summary: 'Read the details of one account' })
  @ApiDataSourceResponseHeader({
    status: HttpStatus.OK,
    description: 'Account details.',
    type: AccountDetailsResponseDto,
  })
  readAccountDetails(
    @Param() { accountId }: AccountIdParamDto,
    @Query() { withBalance }: AccountListQueryDto,
    @ConsentIdHeader() consentId: string,
    @UpstreamContext() context: UpstreamCallContext,
  ): Promise<SourcedResponse<AccountDetailsResponseDto>> {
    return this.accountsService.readAccountDetails(
      { ...context, consentId },
      accountId,
      withBalance === 'true',
    );
  }
}
