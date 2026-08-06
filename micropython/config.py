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

MOTOR_TYPE = _c.get("motor_type", "stepper")   # stepper-only today; kept for future motor types

_pins = _c["pins"]
IN1_PIN         = _pins["in1"]
IN2_PIN         = _pins["in2"]
IN3_PIN         = _pins["in3"]
IN4_PIN         = _pins["in4"]
BUTTON_PIN      = _pins.get("button")   # optional -- feeder has no physical button
LED_PIN         = _pins["led"]

STEPPER_STEP_DELAY_US = _c["stepper"].get("step_delay_us", 2000)   # us per half-step

FEED_DEGREES    = _c["feed"].get("feed_degrees", 720)    # how far one /feed spins the auger
FEED_REVERSE    = _c["feed"].get("feed_reverse", False)  # flip if the auger runs backwards
FEED_COOLDOWN_S = _c["feed"].get("cooldown_s", 30)       # min seconds between feeds
FEED_ANTIJAM_BACK_DEG  = _c["feed"].get("antijam_back_deg", 0)    # anti-jam back-off degrees (0 = off)
FEED_ANTIJAM_EVERY_DEG = _c["feed"].get("antijam_every_deg", 180) # degrees of travel between wiggles

WIFI_SSID     = _c["wifi"]["ssid"]
WIFI_PASSWORD = _c["wifi"]["password"]

TELEGRAM_TOKEN           = _c["telegram"]["token"]
TELEGRAM_ALLOWED_CHATIDS = _c["telegram"]["allowed_chat_ids"]
