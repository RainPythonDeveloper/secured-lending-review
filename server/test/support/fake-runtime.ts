import { Clock } from '../../src/common/runtime/clock.js';
import { RandomSource } from '../../src/common/runtime/random-source.js';
import { Sleeper } from '../../src/common/runtime/sleeper.js';

export class FakeClock extends Clock {
  constructor(private currentMs: number) {
    super();
  }

  nowMs(): number {
    return this.currentMs;
  }

  advanceBy(durationMs: number): void {
    this.currentMs += durationMs;
  }
}

export class RecordingSleeper extends Sleeper {
  readonly sleptDurationsMs: number[] = [];

  sleep(durationMs: number): Promise<void> {
    this.sleptDurationsMs.push(durationMs);
    return Promise.resolve();
  }
}

export class FixedRandomSource extends RandomSource {
  constructor(private readonly fraction: number) {
    super();
  }

  nextFraction(): number {
    return this.fraction;
  }
}
