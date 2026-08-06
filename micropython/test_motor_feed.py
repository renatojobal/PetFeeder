# test_motor_feed.py -- on-device test: one /feed dispenses the configured angle.
#
# Runs on the ESP32 (MicroPython). config.py and motor.py must be on the board.
#
#   ESP_PORT=/dev/cu.usbserial-0001 python tools/espctl.py run test_motor_feed.py
# or at the REPL:  import test_motor_feed
#
# WATCH THE MOTOR: it should spin forward ~FEED_DEGREES (default 720 deg = 2
# turns) and stop. This exercises the exact path the Telegram /feed command
# uses (Motor.run_feed_cycle), and verifies the right number of steps came out.

import time
import config
from motor import Motor, STEPS_PER_REV


def test_feed_dispenses_configured_angle():
    motor = Motor(config)
    expected = config.FEED_DEGREES * STEPS_PER_REV // 360
    print("== feed test: spin {} deg = {} half-steps @ {} us/step ==".format(
        config.FEED_DEGREES, expected, config.STEPPER_STEP_DELAY_US))

    # Track NET travel by summing the direction of every _step. Anti-jam wiggles
    # add reverse steps that cancel out, so net -- not raw count -- must equal the
    # configured angle. `total` also records the raw half-step count for info.
    move = {"net": 0, "total": 0}
    _orig_step = motor._step
    def _counting_step(direction):
        _orig_step(direction)
        move["net"] += direction
        move["total"] += 1
    motor._step = _counting_step

    t0 = time.ticks_ms()
    done = motor.run_feed_cycle()          # exactly what /feed calls (no network ok)
    dt = time.ticks_diff(time.ticks_ms(), t0)

    # --- checks -------------------------------------------------------------
    assert done, "feed cycle reported not completed"
    assert abs(move["net"]) == expected, \
        "net travel {} half-steps, expected {}".format(abs(move["net"]), expected)
    assert motor.state == "stop", "motor not in stop state after feed"
    assert not any(p.value() for p in motor.pins), "coils still energized after feed"

    print("PASS: net {} half-steps ({} deg), {} total incl. wiggle, in {} ms".format(
        abs(move["net"]), config.FEED_DEGREES, move["total"], dt))
    return True


if __name__ == "__main__":
    test_feed_dispenses_configured_angle()
