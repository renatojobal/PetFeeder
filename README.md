# PetFeeder 🐾

A 3D-printed, **ESP32-powered automatic pet feeder** controlled from a **Telegram
bot**. Send `/feed` from your phone and the ESP32 spins an auger to dispense food.

Runs **MicroPython** on the ESP32. The firmware lives in [`micropython/`](micropython/);
this README is the single source of truth for building and running it.

> Fork of [hardrive9000/PetFeeder](https://github.com/hardrive9000/PetFeeder)
> (hardware, 3D parts, schematics). The firmware here is a from-scratch
> MicroPython rewrite with Telegram control, safety guardrails, and a status LED.

## Features

- 📲 **Telegram control** — feed from anywhere: `/feed`, `/stop`, `/status`, …
- 🔒 **Access control** — feeding restricted to an allow-list of chat ids
- 🛡️ **Guardrails** — emergency stop, feed cooldown, busy guard, and anti-flood
  resync (a queue of offline `/feed`s can't dump a pile of food on reconnect)
- 💡 **Status LED** — booting / ready / feeding / error at a glance
- ⚙️ Drives a **28BYJ-48 stepper** via a ULN2003 board — each `/feed` spins the
  auger a fixed angle (default **1080°** = 3 turns), so portions are repeatable

## Hardware

- **ESP32 DevKit V1** (WROOM-32) — verified on ESP32-D0WD-V3.
- **28BYJ-48 stepper motor + ULN2003 driver board** (5 V). The motor is geared
  (~64:1), so the auger turns at ~10–15 RPM — lots of torque, deliberately slow.
  This is expected; a stepper only moves while actively driven, which is exactly
  why the firmware measures a feed in *steps*, not seconds.
- Red **status LED** + resistor (100–330 Ω), and a **470–1000 µF** capacitor across
  the ULN2003 `+`/`−` supply to absorb the coil-current spikes.
- **Power:** the ULN2003 needs a solid **5 V** — the ESP32 `5V`/`VIN` pin (off USB)
  works for testing; a separate 5 V supply is better. **The ESP32 GND and the
  motor-supply GND must be common**, or the motor won't move.
- Wiring diagram in [`Schematic/`](Schematic/) (`pet_feeder_stepper_schematic.png`).

### Pin map (`config.json → pins`)

The four stepper pins go to the ULN2003 board's `IN1`–`IN4` **in order** — a
wrong order makes the motor buzz instead of turning.

| GPIO | Role |
| ---- | ---- |
| 19 (`D19`) | ULN2003 `IN1` |
| 21 (`D21`) | ULN2003 `IN2` |
| 22 (`D22`) | ULN2003 `IN3` |
| 23 (`D23`) | ULN2003 `IN4` |
| 5  (`D5`)  | Status LED |

### 3D-printed parts

In [`3D/`](3D/): `MainBody`, `Hopper`, `LeadScrew_Top` / `LeadScrew_Bottom` (the
auger), `MotorMount`, `Elbow`. (`ServoMount` / `ServoShim` are from the upstream
servo build and are unused with the stepper.)

## Repository layout

```
micropython/  MicroPython firmware (source of truth for the code)
  main.py            entry point (runs at boot): Wi-Fi → motor → LED → bot
  config.py          loads config.json and exposes it as attributes
  config.json.default settings template (copy to config.json)
  wifi.py            Wi-Fi station connect with retry/reconnect
  motor.py           Stepper driver: run_feed_cycle (spin auger N°) / stop
  bot.py             Telegram bot: long-poll, commands, allow-list, guardrails
  led.py             timer-driven status-LED patterns
  test_motor_spin.py on-device test: drive the coils directly (wiring check)
  test_motor_feed.py on-device test: one feed dispenses the configured angle
  tools/espctl.py    host helper: copy files / run scripts / reset the board
  tools/flash.sh     one-command deploy: push firmware + reboot
3D/           STL files for the printed enclosure and auger
Schematic/    Wiring diagram (stepper + ULN2003)
```

---

# Running it on an ESP32

## 1. Prerequisites (on your computer)

```sh
pip install esptool mpremote            # or: pipx install esptool mpremote
export ESP_PORT=/dev/cu.usbserial-XXXX  # your board's port: ls /dev/cu.usb*
```

## 2. Flash MicroPython (one time — wipes any existing firmware)

```sh
esptool --port "$ESP_PORT" flash-id                 # confirm chip = ESP32
esptool --port "$ESP_PORT" erase-flash
esptool --port "$ESP_PORT" --baud 460800 write-flash -z 0x1000 ESP32_GENERIC-vX.Y.Z.bin
```

Download the matching build from https://micropython.org/download/ESP32_GENERIC/.

## 3. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot`, follow the prompts.
2. Copy the **HTTP API token** it gives you.

## 4. Configure

From the `micropython/` directory:

```sh
cd micropython
cp config.json.default config.json    # then edit config.json
```

Fields to set in `config.json`:

| Field | What to put |
| ----- | ----------- |
| `pins.in1`–`in4` | ESP32 GPIOs wired to the ULN2003 `IN1`–`IN4` (defaults 19/21/22/23) |
| `wifi.ssid` / `wifi.password` | Your 2.4 GHz Wi-Fi network |
| `telegram.token` | The BotFather token |
| `telegram.allowed_chat_ids` | Chat ids allowed to feed (see step 6). Leave `[]` to run **open** — anyone who finds the bot can feed |
| `stepper.step_delay_us` | µs per half-step — the motor **speed** (default `1200`). Lower = faster |
| `feed.feed_degrees` | How far the auger spins per `/feed` — your **portion size** (default `1080` = 3 turns) |
| `feed.feed_reverse` | `true` to flip the dispense direction (if the auger runs backwards once loaded) |
| `feed.cooldown_s` | Minimum seconds between feeds (default `30`) |

`config.json` is **gitignored** (it holds your secrets); `config.json.default`
is the committed template.

### Tuning the feeder (portion size & speed)

Only two fields change how a feed looks — no code edits needed. After editing
`config.json`, re-push it with `./tools/flash.sh config.json`.

- **Portion size → `feed.feed_degrees`.** Degrees the auger turns per `/feed`.
  `360` = one full turn, `1080` = three. Bigger number = more food. Dial it in
  by watching how much drops per turn with your food + auger.
- **Speed → `stepper.step_delay_us`.** Microseconds the driver waits between each
  half-step. **Lower is faster.** At the default `1200`, a 3-turn feed (1080°)
  takes ~20 s. Don't go much below `1000`: the 28BYJ-48 has a top step rate, and
  past it the motor just buzzes and stalls (skips steps) instead of turning. If
  it ever stutters or loses torque, raise this value back toward `2000`.

Total feed time ≈ `feed_degrees / 360 × 4096 × step_delay_us`, plus a little
loop overhead. Both are safe to change freely — a wrong value only makes the
motor slower or a portion bigger, never breaks anything.

## 5. Deploy to the board

`tools/flash.sh` pushes the firmware and reboots. It uses `tools/espctl.py`,
which exists because CH340 boards auto-reset when the serial port opens, racing
`mpremote`'s raw-REPL handshake — `espctl` waits for boot before talking.

```sh
# push all runtime files + config.json, then reboot:
./tools/flash.sh

# ...or push just the files you changed:
./tools/flash.sh motor.py config.json
```

**First-time only** — install the `requests` library the bot needs (Wi-Fi must be
set in `config.json`; `mip install` can't enter the raw REPL on CH340, so do it
on-device):

```sh
PY=python3   # any python with pyserial (e.g. mpremote's venv python)
printf 'import wifi, config, mip\nwifi.connect(config)\nmip.install("requests")\n' > /tmp/inst.py
$PY tools/espctl.py run /tmp/inst.py
$PY tools/espctl.py reset
```

## 6. Verify

- **LED:** fast blink (connecting) → a brief blip every ~3 s (online & ready).
- In Telegram, message your bot:
  - `/ping` → `pong` (it's alive and online)
  - `/id` → your chat id — add it to `telegram.allowed_chat_ids`, then re-push
    `config.json` (`./tools/flash.sh config.json`) to lock feeding to you
  - `/feed` → `Feeding...` → the auger spins `feed_degrees` → `Done!`

Watch the logs live in another terminal while you test:

```sh
mpremote connect "$ESP_PORT" repl      # exit with Ctrl-]
```

Once it's running you can power the ESP32 from the 5 V supply and unplug USB —
it reconnects and runs on its own.

## 7. Motor tests (optional, no Wi-Fi)

Two on-device checks. `test_motor_spin.py` drives the coils directly (best
wiring/power check — should turn one way then back). `test_motor_feed.py` runs
the exact path `/feed` uses and verifies the right number of steps come out:

```sh
./tools/flash.sh --no-reset test_motor_spin.py test_motor_feed.py
$PY tools/espctl.py run test_motor_spin.py    # -> shaft turns fwd then back
$PY tools/espctl.py run test_motor_feed.py    # -> PASS: dispensed N half-steps (1080 deg)
$PY tools/espctl.py reset                      # restart the bot
```

- **Turns then reverses** → wiring + power are good.
- **Only buzzes** → the `IN1`–`IN4` order is wrong; swap wires (or `pins` in config).
- **Nothing** → the ULN2003 has no 5 V, or the grounds aren't common.

---

## Telegram commands

| Command | Action | Access |
| ------- | ------ | ------ |
| `/feed`   | Spin the auger `feed_degrees` (default 1080° ≈ 20 s) to dispense a portion | allow-list |
| `/stop`   | Emergency stop — de-energizes the motor (a feed in progress runs to completion) | allow-list |
| `/reboot` | Soft-restart the ESP32 | allow-list |
| `/status` | Motor state, uptime, Wi-Fi IP, last feed, cooldown | open |
| `/ping`   | Liveness check → `pong` | open |
| `/id`     | Show your chat id | open |
| `/help`   | Command list | open |

## Status LED (GPIO5)

| Pattern | State |
| ------- | ----- |
| Fast blink (~5 Hz)       | Booting / connecting to Wi-Fi |
| Blip every ~3 s          | Connected & idle — ready (heartbeat) |
| Solid on                 | Feeding |
| Very fast blink (~10 Hz) | Connection lost / error |

## Deploy tools reference

| Command | Does |
| ------- | ---- |
| `./tools/flash.sh [files…]`      | Push firmware (all runtime files, or just the ones named) and reboot. `--no-reset` skips the reboot |
| `espctl.py put <local> <remote>` | Copy a single file to the board's filesystem |
| `espctl.py run <script>`         | Run a local script on the board, streaming output |
| `espctl.py reset`                | Reboot the board (so `main.py` runs), no REPL interrupt |

Env: `ESP_PORT` selects the serial port; `ESP_RUN_TIMEOUT` (seconds) extends the
`run` timeout.

## Credits & license

Fork of [hardrive9000/PetFeeder](https://github.com/hardrive9000/PetFeeder).
Licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE).
