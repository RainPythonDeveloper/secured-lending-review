import { Controller, Get, Query, Headers } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiHeader, ApiQuery } from '@nestjs/swagger';
import { AccountsService } from './accounts.service.js';
import { AccountsResponseDto } from './dto/account.dto.js';

@ApiTags('Accounts Proxy (AIS)')
@Controller('v1/accounts')
export class AccountsController {
  constructor(private readonly accountsService: AccountsService) {}

  @Get()
  @ApiOperation({
    summary: 'Read Account List',
    description: 'Read the identifiers of the available payment account together with booking balance information.',
  })
  @ApiQuery({
    name: 'withBalance',
    required: false,
    type: Boolean,
    description: 'Reads the list of accessible payment accounts including booking balance.',
    schema: { default: true },
  })
  @ApiHeader({
    name: 'X-Request-ID',
    required: false,
    description: 'ID of the request, unique to the call',
    schema: { type: 'string', default: '757143d5-7537-4e2a-9110-86010def5bf8' },
  })
  @ApiHeader({
    name: 'Consent-ID',
    required: false,
    description: 'Consent identifier granted by PSU',
    schema: { type: 'string', default: '60562021-38e2-4908-b390-a27a8216dfdc' },
  })
  @ApiHeader({
    name: 'PSU-IP-Address',
    required: false,
    description: 'IP Address header field between PSU and TPP',
    schema: { type: 'string', default: '127.0.0.1' },
  })
  @ApiHeader({
    name: 'Accept-Language',
    required: false,
    description: 'HTTP header indicates the natural language',
    schema: { type: 'string', default: 'en' },
  })
  @ApiHeader({
    name: 'Authorization',
    required: false,
    description: 'Bearer authorization token',
    schema: { type: 'string', default: 'Bearer access_apEfyFjTGNTtuad2GZx8oR7C-CeVqOYY' },
  })
  @ApiResponse({
    status: 200,
    description: 'Successful operation',
    type: AccountsResponseDto,
  })
  @ApiResponse({ status: 400, description: 'Bad Request' })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  async getAccounts(
    @Query('withBalance') withBalance?: boolean,
    @Headers() allHeaders?: Record<string, string>,
  ): Promise<AccountsResponseDto> {
    const cleanHeader = (val: string | undefined, fallback: string): string => {
      if (!val) return fallback;
      return val.split(',')[0].trim() || fallback;
    };

    // В Express все входящие заголовки автоматически приводятся к нижнему регистру
    const finalHeaders: Record<string, string> = {
      'accept': 'application/json',
      'X-Request-ID': cleanHeader(allHeaders?.['x-request-id'], '757143d5-7537-4e2a-9110-86010def5bf8'),
      'Consent-ID': cleanHeader(allHeaders?.['consent-id'], '60562021-38e2-4908-b390-a27a8216dfdc'),
      'PSU-IP-Address': cleanHeader(allHeaders?.['psu-ip-address'], '127.0.0.1'),
      'Accept-Language': cleanHeader(allHeaders?.['accept-language'], 'en'),
      'Authorization': cleanHeader(allHeaders?.['authorization'], 'Bearer access_apEfyFjTGNTtuad2GZx8oR7C-CeVqOYY'),
    };

    return await this.accountsService.fetchAccounts(withBalance, finalHeaders);
  }
}