# led.py -- status LED driven by a hardware timer, so it keeps signalling even
# while the main loop is blocked (e.g. inside a 20 s Telegram long-poll).
#
# Modes / patterns (base tick = 50 ms):
#   CONNECTING  ~5 Hz blink      booting / (re)connecting to WiFi
#   READY       brief blip / 3s  connected & idle -- "alive" heartbeat
#   FEEDING     solid on         a feed cycle is running
#   ERROR       ~10 Hz blink     poll failed / connection lost

from machine import Pin, Timer

CONNECTING = 0
READY = 1
FEEDING = 2
ERROR = 3

_TICK_MS = 50


class StatusLED:
    def __init__(self, pin, timer_id=0):
        self._pin = Pin(pin, Pin.OUT)
        self._pin.value(0)
        self._mode = CONNECTING
        self._tick = 0
        self._timer = Timer(timer_id)
        self._timer.init(period=_TICK_MS, mode=Timer.PERIODIC, callback=self._on_tick)

    def set(self, mode):
        self._mode = mode

    def _on_tick(self, t):
        # runs in timer context -- keep it allocation-free (ints + pin only)
        c = self._tick = (self._tick + 1) & 0x3fffffff
        m = self._mode
        if m == FEEDING:
            v = 1
        elif m == ERROR:
            v = c & 1                 # ~10 Hz
        elif m == CONNECTING:
            v = (c >> 1) & 1          # ~5 Hz
        else:                         # READY: 100 ms blip every ~3 s
            v = 1 if (c % 60) < 2 else 0
        self._pin.value(v)

    def deinit(self):
        self._timer.deinit()
        self._pin.value(0)
