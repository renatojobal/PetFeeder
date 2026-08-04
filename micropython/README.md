# Pet Feeder — MicroPython (ESP32)

Python port of the ESP-IDF firmware in [`../Code`](../Code). Drives the feeder
auger with either a **continuous-rotation servo** (default) or a **stepper**,
selectable in `config.json`. WiFi + Telegram control is coming next; this stage
covers motor control and its on-device test.

Verified on an **ESP32-D0WD-V3 (WROOM-32)** running **MicroPython v1.28.0**.

## Files

| File                 | Purpose                                                    |
| -------------------- | ---------------------------------------------------------- |
| `config.json.default`| Settings template (committed). Copy to `config.json`.      |
| `config.json`        | Real settings incl. WiFi/Telegram secrets — **gitignored**.|
| `config.py`          | Loads `config.json` and exposes it as attributes.          |
| `motor.py`           | `Motor` driver: `feed()` / `reverse()` / `stop()` / `run_feed_cycle()`. |
| `test_motor_feed.py` | On-device test: motor feeds for 2 s in a row.              |
| `tools/espctl.py`    | Host-side helper to copy files / run scripts on the board. |

## First-time setup

```sh
cp config.json.default config.json     # then edit config.json (motor_type, WiFi, Telegram)
pip install esptool mpremote           # or: pipx install esptool mpremote
export ESP_PORT=/dev/cu.usbserial-XXXX # your board's port: ls /dev/cu.usb*
```

Set `motor_type` in `config.json` to `"servo"` (default) or `"stepper"`, and
check the pin numbers match your wiring.

## Flash MicroPython (one time, wipes existing firmware)

```sh
esptool --port "$ESP_PORT" flash-id                 # confirm chip = ESP32
esptool --port "$ESP_PORT" erase-flash
esptool --port "$ESP_PORT" --baud 460800 write-flash -z 0x1000 ESP32_GENERIC-vX.Y.Z.bin
```

Download the matching build from https://micropython.org/download/ESP32_GENERIC/.

## Status LED

The red LED on `D5` (GPIO5) is driven by a hardware timer (`led.py`) and shows
the device state at a glance:

| Pattern | State |
| ------- | ----- |
| Fast blink (~5 Hz)   | Booting / connecting to WiFi |
| Blip every ~3 s      | Connected & idle -- ready (heartbeat) |
| Solid on             | Feeding |
| Very fast blink (~10 Hz) | Connection lost / error |

## Run the feed test

This board (CH340) auto-resets whenever the serial port opens, which races
`mpremote`'s raw-REPL handshake ("could not enter raw repl"). `tools/espctl.py`
waits for boot before talking, so use it to copy the files and run the test:

```sh
PY=python3   # any python with pyserial installed
$PY tools/espctl.py put config.json config.json
$PY tools/espctl.py put config.py   config.py
$PY tools/espctl.py put motor.py    motor.py
$PY tools/espctl.py run test_motor_feed.py
```

Watch the motor: it must turn forward continuously for ~2 s without stalling.
Expected output ends with:

```
PASS: fed continuously for 2008 ms over 199 samples, 0 interruptions
```

The test asserts the timing (~2000 ms) and that the drive signal never drops
out mid-feed, then stops the motor. A ~60 ms settle brackets the measurement
because the ESP32 LEDC applies a new PWM duty on the next period (~20 ms @ 50 Hz),
so a read-back taken the instant after `feed()`/`stop()` lags one period.
