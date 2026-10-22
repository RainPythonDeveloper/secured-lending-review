import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { AccountsResponseDto } from './dto/account.dto.js';

@Injectable()
export class AccountsService {
  private readonly tbcApiUrl = 'https://tbc-bank-mock-open-banking-api.vercel.app/0.8/v1/accounts';

  constructor(private readonly httpService: HttpService) {}

  async fetchAccounts(
    withBalance?: boolean,
    headers?: Record<string, string>,
  ): Promise<AccountsResponseDto> {
    const response = await firstValueFrom(
      this.httpService.get<AccountsResponseDto>(this.tbcApiUrl, {
        params: { withBalance },
        headers: {
          'accept': 'application/json',
          ...headers, // Пробрасываем заголовки от клиента (X-Request-ID, Consent-ID, Authorization и т.д.)
        },
      }),
    );
    return response.data;
  }
}