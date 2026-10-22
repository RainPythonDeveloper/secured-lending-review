import { Injectable } from '@nestjs/common';
import { SourcedResponse } from '../../common/data-source/data-source.js';
import type { AisReadContext } from '../providers/ais-data-provider.js';
import { AisProviderResolver } from '../providers/ais-provider-resolver.js';
import type { AccountDetailsResponseDto } from './dto/account-details-response.dto.js';
import type { AccountListDto } from './dto/account-list.dto.js';

@Injectable()
export class AccountsService {
  constructor(private readonly providerResolver: AisProviderResolver) {}

  async listAccounts(
    context: AisReadContext,
    withBalance: boolean,
  ): Promise<SourcedResponse<AccountListDto>> {
    const provider = this.providerResolver.resolve(context.consentId);
    return new SourcedResponse(
      provider.dataSource,
      await provider.listAccounts(context, withBalance),
    );
  }

  async readAccountDetails(
    context: AisReadContext,
    accountId: string,
    withBalance: boolean,
  ): Promise<SourcedResponse<AccountDetailsResponseDto>> {
    const provider = this.providerResolver.resolve(context.consentId);
    return new SourcedResponse(
      provider.dataSource,
      await provider.readAccountDetails(context, accountId, withBalance),
    );
  }
}
