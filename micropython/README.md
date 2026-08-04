# Pet Feeder — MicroPython + Telegram (ESP32)

MicroPython firmware for the ESP32 that drives the feeder and is controlled from
a **Telegram bot**. It's a Python port of the original ESP-IDF firmware in
[`../Code`](../Code), plus Wi-Fi, a Telegram command bot, safety guardrails, and
a status LED.

Drives a **continuous-rotation servo** (default) or a **stepper**, selected in
`config.json`. Verified on an **ESP32-D0WD-V3 (WROOM-32)** running
**MicroPython v1.28.0**.

> ⚠️ **Servo type matters.** The auger needs *continuous rotation*. A standard
> **positional/180° servo will not work** — it jerks to fixed angles instead of
> turning. Use an MG995 360° / MG996R continuous, or a similar continuous servo.

## Files

| File                 | Purpose                                                          |
| -------------------- | ---------------------------------------------------------------- |
| `main.py`            | Entry point (runs at boot): Wi-Fi → motor → LED → bot.           |
| `config.json.default`| Settings template (committed). Copy to `config.json`.            |
| `config.json`        | Real settings incl. Wi-Fi/Telegram secrets — **gitignored**.     |
| `config.py`          | Loads `config.json` and exposes it as attributes.                |
| `wifi.py`            | Wi-Fi station connect with retry/reconnect handling.             |
| `motor.py`           | `Motor` driver: `feed()` / `reverse()` / `stop()` / `run_feed_cycle()`. |
| `bot.py`             | Telegram bot: long-poll, commands, allow-list, guardrails.       |
| `led.py`             | Timer-driven status LED patterns.                                |
| `test_motor_feed.py` | On-device test: motor feeds for 2 s in a row.                    |
| `tools/espctl.py`    | Host-side helper to copy files / run scripts / reset the board.  |

## Telegram commands

| Command | Action |
| ------- | ------ |
| `/feed`   | Run one feed cycle (feed 2 s → reverse 0.5 s → feed 2 s → stop) |
| `/stop`   | Emergency stop — stops the motor, aborts an in-progress feed |
| `/status` | Motor state, uptime, Wi-Fi IP, last feed, cooldown |
| `/ping`   | Liveness check → `pong` |
| `/reboot` | Soft-restart the ESP32 |
| `/id`     | Show your chat id (to fill `allowed_chat_ids`) |
| `/help`   | Command list |

`/feed`, `/stop`, and `/reboot` are restricted to the `allowed_chat_ids` list.
`/start`, `/help`, `/id`, `/ping`, `/status` are open (so you can discover your id).

### Guardrails

- **Anti-flood resync** — on boot *and* after any network outage, the bot
  discards whatever piled up on Telegram's side instead of feeding once per
  queued `/feed`. Only *new* commands act.
- **Cooldown** (`feed.cooldown_s`, default 30 s) — rejects back-to-back feeds.
- **Busy guard** — won't start a feed while one is running.

## Status LED

The red LED on `D5` (GPIO5) is driven by a hardware timer (`led.py`):

| Pattern | State |
| ------- | ----- |
| Fast blink (~5 Hz)       | Booting / connecting to Wi-Fi |
| Blip every ~3 s          | Connected & idle — ready (heartbeat) |
| Solid on                 | Feeding |
| Very fast blink (~10 Hz) | Connection lost / error |

## Pin map (`config.json → pins`)

| GPIO | Role |
| ---- | ---- |
| 18 (`D18`) | Servo signal / stepper step (PWM) |
| 5  (`D5`)  | Status LED |
| 21 (`D21`) | Stepper DIR (stepper only) |
| 22 (`D22`) | Stepper EN (stepper only) |
| 19 (`D19`) | Button — defined but **unused** by this firmware |

## Configuration

Settings live in `config.json` (gitignored — holds your secrets). Copy the
template and edit it:

```sh
cp config.json.default config.json
```

Key fields:

- `motor_type`: `"servo"` or `"stepper"`.
- `wifi.ssid` / `wifi.password`: your network.
- `telegram.token`: from [@BotFather](https://t.me/BotFather).
- `telegram.allowed_chat_ids`: ids allowed to feed. Leave `[]` to run **open**
  (anyone who finds the bot can feed — a warning is logged). Message the bot
  `/id` to learn your chat id, then add it here.
- `servo.feed_rate_us` / `feed_stop_us` / `feed_reversal_us`: continuous-servo
  pulse widths. If the servo **creeps at rest**, tune `feed_stop_us` (~1500);
  if it spins the wrong way or too fast, adjust the other two.
- `feed.feed_ms` / `reverse_ms` / `cooldown_s`: cycle timing + cooldown.

## Prerequisites

```sh
pip install esptool mpremote          # or: pipx install esptool mpremote
export ESP_PORT=/dev/cu.usbserial-XXXX # your board's port: ls /dev/cu.usb*
```

## Flash MicroPython (one time, wipes existing firmware)

```sh
esptool --port "$ESP_PORT" flash-id                 # confirm chip = ESP32
esptool --port "$ESP_PORT" erase-flash
esptool --port "$ESP_PORT" --baud 460800 write-flash -z 0x1000 ESP32_GENERIC-vX.Y.Z.bin
```

Download the matching build from https://micropython.org/download/ESP32_GENERIC/.

## Deploy

The `tools/espctl.py` helper copies files, runs scripts, and resets the board.
(It exists because CH340 boards auto-reset when the serial port opens, which
races `mpremote`'s raw-REPL handshake — `espctl` waits for boot before talking.)

```sh
PY=python3   # any python with pyserial installed
for f in config.json config.py wifi.py motor.py bot.py led.py main.py; do
  $PY tools/espctl.py put "$f" "$f"
done
```

Install the `requests` library the bot needs (HTTPS to the Telegram API). On
this CH340 board `mpremote mip install` can't enter the raw REPL, so install it
on-device — Wi-Fi must be configured in `config.json` first:

```sh
printf 'import wifi, config, mip\nwifi.connect(config)\nmip.install("requests")\n' > /tmp/inst.py
$PY tools/espctl.py run /tmp/inst.py
# (on a board where mpremote works: mpremote connect "$ESP_PORT" mip install requests)
```

Finally, reboot so `main.py` runs the bot:

```sh
$PY tools/espctl.py reset
```

On boot `main.py` connects Wi-Fi, then the bot starts polling. Watch the LED:
fast blink → ~3 s heartbeat means it's online. Send `/ping` from Telegram to
confirm, then `/feed`.

## Run the feed test

Motor-only sanity check (no Wi-Fi needed):

```sh
$PY tools/espctl.py put config.json config.json
$PY tools/espctl.py put config.py   config.py
$PY tools/espctl.py put motor.py    motor.py
$PY tools/espctl.py run test_motor_feed.py
```

Expected output ends with:

```
PASS: fed continuously for 2008 ms over 199 samples, 0 interruptions
```

The test asserts the timing (~2000 ms) and that the drive signal never drops out
mid-feed, then stops the motor. A ~60 ms settle brackets the measurement because
the ESP32 LEDC applies a new PWM duty on the next period (~20 ms @ 50 Hz), so a
read-back taken the instant after `feed()`/`stop()` lags one period.

## `espctl` reference

| Command | Does |
| ------- | ---- |
| `espctl.py put <local> <remote>` | Copy a file to the board's filesystem |
| `espctl.py run <script>`         | Run a local script on the board, streaming output |
| `espctl.py reset`                | Reboot the board (so `main.py` runs), no REPL interrupt |

Set `ESP_PORT` to select the serial port; `ESP_RUN_TIMEOUT` (seconds) to extend
the `run` timeout.
