# test_motor_feed.py -- on-device test: the motor keeps feeding for 2 s straight.
#
# Runs on the ESP32 (MicroPython). config.py and motor.py must be on the board.
# Easiest way to run without copying files permanently:
#
#   mpremote connect /dev/tty.usbserial-XXXX mount . run test_motor_feed.py
#
# or copy the three files to the board and, at the REPL:
#
#   import test_motor_feed
#
# WATCH THE MOTOR while it runs: it must turn forward continuously for ~2 s
# without stalling or clogging. The script also verifies the timing and that
# the drive signal never drops out mid-feed.

import time
import config
from motor import Motor

FEED_TARGET_MS = 2000   # must feed continuously for this long
TOLERANCE_MS   = 150    # allow small scheduling slack on the measured duration
SAMPLE_MS      = 10     # how often we re-check the hardware state
PROGRESS_MS    = 250    # how often we print a progress line
SETTLE_MS      = 60     # let the PWM signal latch before we start checking
                        # (LEDC applies a new duty on the next period: ~20 ms @ 50 Hz)


def test_feed_two_seconds_in_a_row():
    motor = Motor(config)
    print("== feed test: {} motor, target {} ms ==".format(config.MOTOR_TYPE, FEED_TARGET_MS))

    interruptions = 0     # samples where the motor was NOT feeding
    samples = 0
    next_progress = PROGRESS_MS

    try:
        motor.feed()
        time.sleep_ms(SETTLE_MS)   # motor is already feeding; wait for the signal to latch
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < FEED_TARGET_MS:
            samples += 1
            if not motor.is_feeding():
                interruptions += 1
            elapsed = time.ticks_diff(time.ticks_ms(), start)
            if elapsed >= next_progress:
                print("  feeding... {} ms".format(elapsed))
                next_progress += PROGRESS_MS
            time.sleep_ms(SAMPLE_MS)
        elapsed = time.ticks_diff(time.ticks_ms(), start)
    finally:
        motor.stop()             # always stop, even if interrupted or an assert fires
        time.sleep_ms(SETTLE_MS)  # let the stop signal latch before we verify it

    # --- checks -------------------------------------------------------------
    assert interruptions == 0, \
        "motor dropped out of feed on {}/{} samples".format(interruptions, samples)
    assert elapsed >= FEED_TARGET_MS - TOLERANCE_MS, \
        "fed for only {} ms (< {} ms)".format(elapsed, FEED_TARGET_MS - TOLERANCE_MS)
    assert not motor.is_feeding(), "motor still feeding after stop()"

    print("PASS: fed continuously for {} ms over {} samples, 0 interruptions".format(
        elapsed, samples))
    return True


if __name__ == "__main__":
    test_feed_two_seconds_in_a_row()
