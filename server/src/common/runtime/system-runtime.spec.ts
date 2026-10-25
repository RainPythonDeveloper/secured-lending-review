import { SystemClock } from './clock.js';
import { MathRandomSource } from './random-source.js';
import { TimerSleeper } from './sleeper.js';

describe('system runtime', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('SystemClock reports the current epoch time in milliseconds', () => {
    vi.useFakeTimers({ now: new Date('2026-10-22T10:00:00Z') });

    const nowMs = new SystemClock().nowMs();

    expect(nowMs).toBe(Date.parse('2026-10-22T10:00:00Z'));
  });

  it('TimerSleeper resolves only after the requested duration', async () => {
    vi.useFakeTimers();
    let hasWoken = false;
    const sleeping = new TimerSleeper().sleep(250).then(() => {
      hasWoken = true;
    });

    await vi.advanceTimersByTimeAsync(249);
    const hasWokenEarly = hasWoken;
    await vi.advanceTimersByTimeAsync(1);
    await sleeping;

    expect(hasWokenEarly).toBe(false);
    expect(hasWoken).toBe(true);
  });

  it('MathRandomSource returns a fraction in [0, 1)', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.42);

    const fraction = new MathRandomSource().nextFraction();

    expect(fraction).toBe(0.42);
  });
});
