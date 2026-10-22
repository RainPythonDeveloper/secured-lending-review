import { Injectable } from '@nestjs/common';

export abstract class Clock {
  abstract nowMs(): number;
}

@Injectable()
export class SystemClock extends Clock {
  nowMs(): number {
    return Date.now();
  }
}
