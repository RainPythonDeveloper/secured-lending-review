import {
  Global,
  Module,
  type MiddlewareConsumer,
  type NestModule,
} from '@nestjs/common';
import { RequestIdMiddleware } from './request-id/request-id.middleware.js';
import { Clock, SystemClock } from './runtime/clock.js';
import { MathRandomSource, RandomSource } from './runtime/random-source.js';
import { Sleeper, TimerSleeper } from './runtime/sleeper.js';

@Global()
@Module({
  providers: [
    { provide: Clock, useClass: SystemClock },
    { provide: Sleeper, useClass: TimerSleeper },
    { provide: RandomSource, useClass: MathRandomSource },
  ],
  exports: [Clock, Sleeper, RandomSource],
})
export class CommonModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(RequestIdMiddleware).forRoutes('*');
  }
}
