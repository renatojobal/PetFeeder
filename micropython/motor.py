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

# 28BYJ-48 Half-step sequence for ULN2003
_SEQ = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1],
]

class Motor:
    """Drives the feeder auger with either a stepper or a continuous servo.

    States: "feed" (forward), "reverse" (anti-clog), "stop".
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.type = cfg.MOTOR_TYPE
        self._state = "stop"
        self._step_idx = 0
        self._dir = 1 # 1 or -1

        if self.type == STEPPER:
            self.pins = [
                Pin(cfg.IN1_PIN, Pin.OUT),
                Pin(cfg.IN2_PIN, Pin.OUT),
                Pin(cfg.IN3_PIN, Pin.OUT),
                Pin(cfg.IN4_PIN, Pin.OUT),
            ]
            self.stop()
            self.step_delay = 1500 # 1.5ms per step, adjustable
        else:
            self.pwm = PWM(Pin(cfg.PWM_PIN)) # Note: this may fail if servo uses IN1, but let's assume stepper for now
            self.pwm.freq(cfg.SERVO_FREQ)
            self.pwm.duty_ns(cfg.FEED_STOP_US * 1000)

    # -- low-level state changes ---------------------------------------------
    def feed(self):
        """Drive the auger forward and keep going until stop()/reverse()."""
        if self.type == STEPPER:
            self._dir = -1
        else:
            self.pwm.duty_ns(self.cfg.FEED_RATE_US * 1000)
        self._state = "feed"

    def reverse(self):
        """Reverse briefly to clear clogs."""
        if self.type == STEPPER:
            self._dir = 1
        else:
            self.pwm.duty_ns(self.cfg.FEED_REVERSAL_US * 1000)
        self._state = "reverse"

    def stop(self):
        """Stop the motor."""
        if self.type == STEPPER:
            for p in self.pins:
                p.value(0)
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
            return self._state == "feed"
        return abs(self.pwm.duty_ns() - self.cfg.FEED_RATE_US * 1000) < _SERVO_TOL_NS

    # -- high-level routine ---------------------------------------------------
    def _step(self):
        self._step_idx = (self._step_idx + self._dir) % len(_SEQ)
        seq = _SEQ[self._step_idx]
        for i, val in enumerate(seq):
            self.pins[i].value(val)

    def _hold(self, ms, ok):
        """Run for ``ms`` (accurate regardless of ok() cost), checking ok()
        along the way. Returns False if ok() asks to abort."""
        end = time.ticks_add(time.ticks_ms(), ms)
        last_ok_check = time.ticks_ms()
        
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            if time.ticks_diff(time.ticks_ms(), last_ok_check) > 50:
                if ok is not None and not ok():
                    return False
                last_ok_check = time.ticks_ms()
            
            if self.type == STEPPER:
                self._step()
                time.sleep_us(self.step_delay)
            else:
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
