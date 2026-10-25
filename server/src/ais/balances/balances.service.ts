import { Injectable } from '@nestjs/common';
import { SourcedResponse } from '../../common/data-source/data-source.js';
import type { AisReadContext } from '../providers/ais-data-provider.js';
import { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import type { ReadAccountBalanceResponseDto } from './dto/read-account-balance-response.dto.js';

@Injectable()
export class BalancesService {
  constructor(private readonly providerResolver: AisProviderResolver) {}

  async readBalances(
    context: AisReadContext,
    accountId: string,
  ): Promise<SourcedResponse<ReadAccountBalanceResponseDto>> {
    const provider = this.providerResolver.resolve(context.consentId);
    return new SourcedResponse(
      provider.dataSource,
      await provider.readBalances(context, accountId),
    );
  }
}
