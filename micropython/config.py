# config.py -- loads settings from config.json and exposes them as attributes.
#
# config.json is gitignored (holds your WiFi/Telegram secrets); copy the
# template if it's missing:  cp config.json.default config.json
#
# Works on both MicroPython (on the ESP32) and host CPython.

import json

try:
    with open("config.json") as _f:
        _c = json.load(_f)
except OSError:
    raise OSError("config.json not found -- run: cp config.json.default config.json")

MOTOR_TYPE = _c["motor_type"]

_pins = _c["pins"]
IN1_PIN         = _pins["in1"]
IN2_PIN         = _pins["in2"]
IN3_PIN         = _pins["in3"]
IN4_PIN         = _pins["in4"]
BUTTON_PIN      = _pins["button"]
LED_PIN         = _pins["led"]

STEPPER_FREQ = _c["stepper"]["freq"]
STEPPER_DUTY = _c["stepper"]["duty"]

SERVO_FREQ       = _c["servo"]["freq"]
FEED_RATE_US     = _c["servo"]["feed_rate_us"]
FEED_REVERSAL_US = _c["servo"]["feed_reversal_us"]
FEED_STOP_US     = _c["servo"]["feed_stop_us"]

FEED_MS         = _c["feed"]["feed_ms"]
REVERSE_MS      = _c["feed"]["reverse_ms"]
FEED_COOLDOWN_S = _c["feed"].get("cooldown_s", 30)   # min seconds between feeds

WIFI_SSID     = _c["wifi"]["ssid"]
WIFI_PASSWORD = _c["wifi"]["password"]

TELEGRAM_TOKEN           = _c["telegram"]["token"]
TELEGRAM_ALLOWED_CHATIDS = _c["telegram"]["allowed_chat_ids"]
