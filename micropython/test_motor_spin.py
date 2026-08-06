# test_motor_spin.py -- lowest-level wiring check for the 28BYJ-48 + ULN2003.
#
# This bypasses ALL feed/bot logic and steps the four coils directly. It's the
# fastest way to tell a wiring problem from a code problem:
#
#   * shaft turns one way then back  -> wiring + power are GOOD
#   * only buzzes / vibrates         -> coil ORDER is wrong (swap IN wires/pins)
#   * nothing at all                 -> no 5V on the ULN2003, or GND not shared
#
# The 4 LEDs on the ULN2003 board should chase in a smooth pattern while it runs;
# if they light but the shaft doesn't move, it's power (the motor needs a real 5V,
# not 3.3V), not logic.
#
# Run it (files must be on the board or mounted):
#   mpremote connect /dev/tty.usbserial-XXXX mount . run test_motor_spin.py
# or at the board REPL:
#   import test_motor_spin

import time
import config
from machine import Pin

# 28BYJ-48 half-step sequence -- identical to the one motor.py uses.
_SEQ = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]

STEP_DELAY_MS = 2       # 2 ms/step: safe, reliable speed for the 28BYJ-48
STEPS_PER_REV = 4096    # half-steps per full revolution of the OUTPUT shaft

_pins = [
    Pin(config.IN1_PIN, Pin.OUT),
    Pin(config.IN2_PIN, Pin.OUT),
    Pin(config.IN3_PIN, Pin.OUT),
    Pin(config.IN4_PIN, Pin.OUT),
]


def _apply(step):
    for i in range(4):
        _pins[i].value(step[i])


def _release():
    # De-energize the coils so they don't sit hot / waste ~240 mA when idle.
    for p in _pins:
        p.value(0)


def spin(steps, direction):
    """Step `steps` half-steps. direction = 1 (forward) or -1 (reverse)."""
    idx = 0
    try:
        for n in range(steps):
            idx = (idx + direction) % len(_SEQ)
            _apply(_SEQ[idx])
            time.sleep_ms(STEP_DELAY_MS)
            if n % 512 == 0:
                print("  step {}/{}".format(n, steps))
    finally:
        _release()


def test_spin():
    print("== spin test on pins IN1={} IN2={} IN3={} IN4={} ==".format(
        config.IN1_PIN, config.IN2_PIN, config.IN3_PIN, config.IN4_PIN))
    print("forward one full revolution (~{:.1f}s)...".format(
        STEPS_PER_REV * STEP_DELAY_MS / 1000))
    spin(STEPS_PER_REV, 1)
    time.sleep_ms(500)
    print("reverse one full revolution...")
    spin(STEPS_PER_REV, -1)
    _release()
    print("DONE: shaft turned one way then back -> wiring + power are good.")
    print("      only buzzed -> coil order wrong. nothing -> check 5V + shared GND.")
    return True


if __name__ == "__main__":
    test_spin()
