import { buildAccountLinks, buildTransactionLinks } from './account-links.js';

describe('buildAccountLinks', () => {
  it('links the account, its balances and its transactions to gateway routes', () => {
    const links = buildAccountLinks('acc-gel-001');

    expect(links).toEqual({
      account: { href: '/v1/accounts/acc-gel-001' },
      balances: { href: '/v1/accounts/acc-gel-001/balances' },
      transactions: { href: '/v1/accounts/acc-gel-001/transactions' },
    });
  });

  it('encodes a resource id that is not safe in a URL path', () => {
    const links = buildAccountLinks('acc/1 2');

    expect(links.account).toEqual({ href: '/v1/accounts/acc%2F1%202' });
  });
});

describe('buildTransactionLinks', () => {
  it('links a transaction report to the gateway account route', () => {
    const links = buildTransactionLinks('ACC-0024');

    expect(links).toEqual({ account: { href: '/v1/accounts/ACC-0024' } });
  });
});
