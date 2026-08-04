# PetFeeder 🐾

A 3D-printed, ESP32-powered automatic pet feeder.

This is a fork of [**hardrive9000/PetFeeder**](https://github.com/hardrive9000/PetFeeder)
that adds a **MicroPython firmware with Telegram control** alongside the original
ESP-IDF (C) firmware. The hardware, 3D parts, and schematics are unchanged — you
just pick which firmware to run.

## What this fork adds

|              | Original (upstream, `Code/`)      | This fork adds (`micropython/`)                    |
| ------------ | --------------------------------- | -------------------------------------------------- |
| Language     | ESP-IDF / C                       | MicroPython                                         |
| Control      | Local Wi-Fi web page + button     | **Telegram bot** — feed from anywhere              |
| Feedback     | LED on during feed                | Status-LED **patterns** (booting / ready / feeding / error) |
| Safety       | —                                 | Emergency `/stop`, feed **cooldown**, busy guard, anti-flood resync |

Both firmwares drive the same feeder; run one or the other.

## Hardware

- **ESP32 DevKit V1** (WROOM-32) — verified on ESP32-D0WD-V3.
- **Continuous-rotation servo** (MG995 360° / MG996R continuous).
  ⚠️ The auger needs **continuous rotation** — a standard **positional/180° servo
  will not work** (it jerks to angles instead of turning). A stepper is also supported.
- Red **status LED** + resistor (100–330 Ω), **470 µF** capacitor across the servo
  power, and a **5 V supply capable of ≥1.5–2 A** (the servo alone pulls ~1 A).
- Wiring diagrams: [`Schematic/`](Schematic/) — `pet_feeder_servo_schematic.png`
  and `pet_feeder_stepper_schematic.png`.

## 3D-printed parts

In [`3D/`](3D/): `MainBody`, `Hopper`, `LeadScrew_Top` / `LeadScrew_Bottom` (the
auger), `ServoMount`, `ServoShim`, `MotorMount`, `Elbow`.

## Repository layout

```
Code/         Original ESP-IDF (C) firmware — web page + button control
micropython/  MicroPython firmware — Wi-Fi + Telegram bot (see its README)
3D/           STL files for the printed enclosure and auger
Schematic/    Wiring diagrams (servo and stepper variants)
LICENSE       Apache License 2.0
```

## Firmware options

### 🐍 MicroPython + Telegram — recommended · [`micropython/`](micropython/)

Wi-Fi station + a Telegram bot that drives the feeder, with guardrails and a
status LED. Control it from your phone, anywhere.

Bot commands: `/feed`, `/stop`, `/status`, `/ping`, `/reboot`, `/id`, `/help`
(feeding is restricted to an allow-list of chat ids).

👉 **Full setup, flashing, and usage: [`micropython/README.md`](micropython/README.md).**

### ⚙️ Original ESP-IDF (C) — [`Code/`](Code/)

The upstream firmware: connects to Wi-Fi, serves an on/off web page on the local
network, and feeds on a button press. Build with the ESP-IDF toolchain
(`idf.py build flash`); Wi-Fi credentials are set via `idf.py menuconfig`. Choose
stepper vs. servo with the `STEPPER_MOTOR` define in `Code/main/main.c`.

## Credits & license

Fork of [hardrive9000/PetFeeder](https://github.com/hardrive9000/PetFeeder).
Licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE).
