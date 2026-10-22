import { HealthService } from './health.service.js';

describe('HealthService', () => {
  it('reports the gateway status as ok', () => {
    const healthService = new HealthService();

    const health = healthService.getStatus();

    expect(health).toEqual({ status: 'ok' });
  });
});
