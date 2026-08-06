# motor.py -- feeder auger stepper driver for MicroPython / ESP32.
#
# Drives a 28BYJ-48 stepper through a ULN2003 board. One /feed spins the auger
# forward by cfg.FEED_DEGREES at cfg.STEPPER_STEP_DELAY_US per half-step.
#
# The feed is measured in STEPS (a fixed rotation), not wall-clock time: an
# optional ok() callback can stretch how LONG a feed takes but never changes how
# FAR the auger turns. A stepper only moves while it is actively stepped, so this
# matters.
#
# Stepper-only by design. Other motor types (continuous servo, DC + encoder, ...)
# were removed; a future layered rewrite can reintroduce them behind a common
# Motor interface -- see README.

import time
from machine import Pin

# 28BYJ-48 half-step sequence for ULN2003 (drives IN1..IN4 in order).
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

# Half-steps per full revolution of the OUTPUT shaft (28BYJ-48 is ~64:1 geared).
STEPS_PER_REV = 4096


class Motor:
    """Drives the feeder auger with a 28BYJ-48 stepper via a ULN2003 driver."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._state = "stop"
        self._step_idx = 0
        self.pins = [
            Pin(cfg.IN1_PIN, Pin.OUT),
            Pin(cfg.IN2_PIN, Pin.OUT),
            Pin(cfg.IN3_PIN, Pin.OUT),
            Pin(cfg.IN4_PIN, Pin.OUT),
        ]
        self.step_delay = cfg.STEPPER_STEP_DELAY_US    # us per half-step
        self.feed_degrees = cfg.FEED_DEGREES           # how far one /feed turns
        # Anti-jam: every antijam_every_deg of travel, back off antijam_back_deg
        # then push forward again to shake loose a stuck kibble. Smaller interval
        # = more frequent wiggles. back_deg = 0 disables it (one continuous spin).
        self.antijam_back_deg = getattr(cfg, "FEED_ANTIJAM_BACK_DEG", 0)
        self.antijam_every_deg = getattr(cfg, "FEED_ANTIJAM_EVERY_DEG", 180)
        # Which way dispenses food. Flip feed.feed_reverse in config.json if the
        # auger pushes food the wrong way once it's loaded (no code change).
        self._dispense_dir = 1 if getattr(cfg, "FEED_REVERSE", False) else -1
        self.stop()

    # -- introspection (used by tests / bot status) --------------------------
    @property
    def state(self):
        return self._state

    def is_feeding(self):
        return self._state == "feed"

    # -- low level ------------------------------------------------------------
    def _step(self, direction):
        self._step_idx = (self._step_idx + direction) % len(_SEQ)
        seq = _SEQ[self._step_idx]
        for i, val in enumerate(seq):
            self.pins[i].value(val)

    def stop(self):
        """Stop and de-energize the coils (so they don't sit hot / draw current)."""
        for p in self.pins:
            p.value(0)
        self._state = "stop"

    # -- high-level routine ---------------------------------------------------
    def run_feed_cycle(self, ok=None):
        """Dispense one portion: spin the auger forward by cfg.FEED_DEGREES.

        If antijam_back_deg > 0, every antijam_every_deg of forward travel the
        auger backs off that many degrees and re-advances the same amount before
        continuing -- a wiggle to break a jam. It's position-neutral, so the net
        forward travel is always exactly FEED_DEGREES.

        ok: optional callback checked ~every 50 ms; return False to abort.
        Returns True if it completed, False if aborted. The motor is always left
        stopped either way.
        """
        total = self.feed_degrees * STEPS_PER_REV // 360
        interval = max(1, self.antijam_every_deg * STEPS_PER_REV // 360)  # steps between wiggles
        back = self.antijam_back_deg * STEPS_PER_REV // 360    # steps to back off
        self._state = "feed"
        self._last_ok_check = time.ticks_ms()
        try:
            done = 0
            while done < total:
                # Forward to the next wiggle boundary (or the end).
                segment = min(interval, total - done)
                if not self._spin(segment, self._dispense_dir, ok):
                    return False
                done += segment
                # Anti-jam wiggle between segments (never after the last one).
                if back and done < total:
                    if not self._spin(back, -self._dispense_dir, ok):
                        return False
                    if not self._spin(back, self._dispense_dir, ok):
                        return False
            return True
        finally:
            self.stop()

    def _spin(self, steps, direction, ok):
        """Step `steps` half-steps in `direction`, honouring the ok() callback.
        Returns False if ok() aborted, True otherwise."""
        for _ in range(steps):
            self._step(direction)
            time.sleep_us(self.step_delay)
            if time.ticks_diff(time.ticks_ms(), self._last_ok_check) > 50:
                if ok is not None and not ok():
                    return False
                self._last_ok_check = time.ticks_ms()
        return True
