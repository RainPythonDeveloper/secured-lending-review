import { setTimeout as waitFor } from 'node:timers/promises';
import { Injectable } from '@nestjs/common';

export abstract class Sleeper {
  abstract sleep(durationMs: number): Promise<void>;
}

@Injectable()
export class TimerSleeper extends Sleeper {
  async sleep(durationMs: number): Promise<void> {
    await waitFor(durationMs);
  }
}
