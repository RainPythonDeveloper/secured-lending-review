import { Injectable } from '@nestjs/common';

export abstract class RandomSource {
  /** Returns a number in the range [0, 1). */
  abstract nextFraction(): number;
}

@Injectable()
export class MathRandomSource extends RandomSource {
  nextFraction(): number {
    return Math.random();
  }
}
