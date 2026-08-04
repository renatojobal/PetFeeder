# motor.py -- feeder motor driver (stepper or servo) for MicroPython / ESP32
#
# Ports the feed() logic from ../Code/main/main.c. Same states, same timing,
# but exposes small hooks (state / is_feeding) so tests can watch what the
# hardware is actually doing.

import time
from machine import Pin, PWM

STEPPER = "stepper"
SERVO   = "servo"

# how close a servo pulse read-back must be to count as "the same" (ns)
_SERVO_TOL_NS = 20_000


class Motor:
    """Drives the feeder auger with either a stepper or a continuous servo.

    States: "feed" (forward), "reverse" (anti-clog), "stop".
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.type = cfg.MOTOR_TYPE
        self._state = "stop"

        if self.type == STEPPER:
            self.dir = Pin(cfg.STEPPER_DIR_PIN, Pin.OUT)
            self.en  = Pin(cfg.STEPPER_EN_PIN, Pin.OUT)
            self.en.value(1)      # driver disabled (active low)
            self.dir.value(1)     # forward
            self.pwm = PWM(Pin(cfg.PWM_PIN))
            self.pwm.freq(cfg.STEPPER_FREQ)
            self.pwm.duty_u16(0)  # not stepping
        else:
            self.pwm = PWM(Pin(cfg.PWM_PIN))
            self.pwm.freq(cfg.SERVO_FREQ)
            self.pwm.duty_ns(cfg.FEED_STOP_US * 1000)

    # -- low-level state changes ---------------------------------------------
    def feed(self):
        """Drive the auger forward and keep going until stop()/reverse()."""
        if self.type == STEPPER:
            self.en.value(0)                         # enable driver
            self.dir.value(1)                        # forward
            self.pwm.duty_u16(self.cfg.STEPPER_DUTY)
        else:
            self.pwm.duty_ns(self.cfg.FEED_RATE_US * 1000)
        self._state = "feed"

    def reverse(self):
        """Reverse briefly to clear clogs."""
        if self.type == STEPPER:
            self.en.value(0)                         # keep driver enabled
            self.dir.value(0)                        # reverse
            self.pwm.duty_u16(self.cfg.STEPPER_DUTY)
        else:
            self.pwm.duty_ns(self.cfg.FEED_REVERSAL_US * 1000)
        self._state = "reverse"

    def stop(self):
        """Stop the motor."""
        if self.type == STEPPER:
            self.pwm.duty_u16(0)
            self.en.value(1)                         # disable driver
        else:
            self.pwm.duty_ns(self.cfg.FEED_STOP_US * 1000)
        self._state = "stop"

    # -- introspection (used by tests) ---------------------------------------
    @property
    def state(self):
        return self._state

    def is_feeding(self):
        """True when the hardware is actually driving a forward feed."""
        if self.type == STEPPER:
            return (self.en.value() == 0
                    and self.dir.value() == 1
                    and self.pwm.duty_u16() > 0)
        return abs(self.pwm.duty_ns() - self.cfg.FEED_RATE_US * 1000) < _SERVO_TOL_NS

    # -- high-level routine ---------------------------------------------------
    def _hold(self, ms, ok):
        """Run for ``ms`` (accurate regardless of ok() cost), checking ok()
        along the way. Returns False if ok() asks to abort."""
        end = time.ticks_add(time.ticks_ms(), ms)
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            if ok is not None and not ok():
                return False
            time.sleep_ms(50)
        return True

    def run_feed_cycle(self, ok=None):
        """Full dispense: feed 2 s -> reverse 0.5 s -> feed 2 s -> stop.

        ok: optional callback checked periodically; return False to abort.
        Returns True if it completed, False if aborted. The motor is always
        left stopped either way.
        """
        try:
            self.feed()
            if not self._hold(self.cfg.FEED_MS, ok):
                return False
            self.reverse()
            if not self._hold(self.cfg.REVERSE_MS, ok):
                return False
            self.feed()
            if not self._hold(self.cfg.FEED_MS, ok):
                return False
        finally:
            self.stop()
        return True
