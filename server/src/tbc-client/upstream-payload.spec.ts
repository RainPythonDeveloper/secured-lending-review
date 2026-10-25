import { Type } from 'class-transformer';
import { IsArray, IsString, Matches, ValidateNested } from 'class-validator';
import { loadSandboxFixture } from '../../test/fixtures/load-fixture.js';
import { parseUpstreamPayload } from './upstream-payload.js';

class ProbeAmountDto {
  @IsString()
  currency: string;

  @IsString()
  @Matches(/^-?\d{1,14}(\.\d{1,3})?$/)
  amount: string;
}

class ProbeBalanceDto {
  @IsString()
  balanceType: string;

  @ValidateNested()
  @Type(() => ProbeAmountDto)
  balanceAmount: ProbeAmountDto;
}

class ProbeBalancesDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => ProbeBalanceDto)
  balances: ProbeBalanceDto[];
}

const contractViolation = (detail: unknown) => ({
  problem: expect.objectContaining({
    status: 502,
    code: 'UPSTREAM_CONTRACT_VIOLATION',
    detail,
  }),
});

describe('parseUpstreamPayload', () => {
  it('parses a sandbox fixture into the DTO and strips unknown fields', () => {
    const body = loadSandboxFixture('balances.acc-gel-001.200.json');

    const payload = parseUpstreamPayload(
      ProbeBalancesDto,
      body,
      'readBalances',
    );

    expect(payload).toBeInstanceOf(ProbeBalancesDto);
    expect(payload).not.toHaveProperty('account');
    expect(payload.balances[0]).toEqual({
      balanceType: 'interimBooked',
      balanceAmount: { currency: 'GEL', amount: '3247.50' },
    });
  });

  it('rejects a numeric amount as an upstream contract violation', () => {
    const body = {
      balances: [
        {
          balanceType: 'interimBooked',
          balanceAmount: { currency: 'GEL', amount: 3247.5 },
        },
      ],
    };

    expect(() =>
      parseUpstreamPayload(ProbeBalancesDto, body, 'readBalances'),
    ).toThrow(
      expect.objectContaining(
        contractViolation(
          expect.stringMatching(
            /^TBC sandbox response to readBalances does not match the specification: balances\.0\.balanceAmount\.amount: amount must /,
          ),
        ),
      ),
    );
  });

  it.each([
    ['undefined', undefined],
    ['an array', []],
    ['a string', 'ok'],
  ])('rejects a body that is %s', (_case, body) => {
    expect(() =>
      parseUpstreamPayload(ProbeBalancesDto, body, 'readBalances'),
    ).toThrow(
      expect.objectContaining(
        contractViolation(
          'TBC sandbox response to readBalances does not match the specification: body is not a JSON object',
        ),
      ),
    );
  });
});
