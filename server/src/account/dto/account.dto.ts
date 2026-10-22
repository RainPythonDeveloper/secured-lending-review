import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class BalanceAmountDto {
  @ApiProperty({ example: 'GEL' })
  currency: string;

  @ApiProperty({ example: '3247.50' })
  amount: string;
}

export class BalanceDto {
  @ApiProperty({ type: BalanceAmountDto })
  balanceAmount: BalanceAmountDto;

  @ApiProperty({ example: 'interimBooked' })
  balanceType: string;

  @ApiProperty({ example: false })
  creditLimitIncluded: boolean;

  @ApiProperty({ example: '2026-10-20' })
  referenceDate: string;

  @ApiProperty({ example: '2026-10-20T09:00:00+04:00' })
  lastChangeDateTime: string;
}

export class LinkItemDto {
  @ApiProperty({ example: '/0.8/v1/accounts/acc-gel-001' })
  href: string;
}

export class AccountLinksDto {
  @ApiProperty({ type: LinkItemDto })
  account: LinkItemDto;

  @ApiProperty({ type: LinkItemDto })
  balances: LinkItemDto;

  @ApiProperty({ type: LinkItemDto })
  transactions: LinkItemDto;
}

export class AccountDto {
  @ApiProperty({ example: 'acc-gel-001' })
  resourceId: string;

  @ApiProperty({ example: 'GE11TB1000000000000010' })
  iban: string;

  @ApiProperty({ example: 'GEL' })
  currency: string;

  @ApiProperty({ example: 'Demo current account' })
  name: string;

  @ApiPropertyOptional({ example: 'ყოველდღიური ანგარიში' })
  displayName?: string;

  @ApiProperty({ example: 'მოქი მოქიაშვილი' })
  ownerName: string;

  @ApiProperty({ example: 'CACC' })
  cashAccountType: string;

  @ApiProperty({ example: 'enabled' })
  status: string;

  @ApiProperty({ example: 'TBCBGE22' })
  bic: string;

  @ApiProperty({ example: 'PRIV' })
  usage: string;

  @ApiProperty({ type: [BalanceDto] })
  balances: BalanceDto[];

  @ApiProperty({ type: AccountLinksDto })
  _links: AccountLinksDto;
}

export class AccountsResponseDto {
  @ApiProperty({ type: [AccountDto] })
  accounts: AccountDto[];
}