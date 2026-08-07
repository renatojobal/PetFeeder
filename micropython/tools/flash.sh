#!/usr/bin/env bash
# flash.sh -- push the MicroPython firmware to the ESP32 and reboot it.
#
# Uses espctl.py (not mpremote) because the CH340 auto-resets on port open and
# races mpremote's raw-REPL handshake. espctl waits for boot and is reliable.
#
# Usage:
#   ./tools/flash.sh                 # push all runtime files + config, then reset
#   ./tools/flash.sh motor.py        # push only the files you name, then reset
#   ./tools/flash.sh --no-reset a.py # push without rebooting afterwards
#
# Override the port if it ever differs:  ESP_PORT=/dev/cu.usbserial-XXXX ./tools/flash.sh
set -euo pipefail

cd "$(dirname "$0")/.."                       # -> the micropython/ directory
export ESP_PORT="${ESP_PORT:-/dev/cu.usbserial-0001}"

# espctl needs pyserial; the system python3 usually lacks it, but the mpremote
# pipx venv has it. Prefer that; fall back to python3 if the path is gone.
PY="${PY:-$HOME/.local/pipx/venvs/mpremote/bin/python}"
[ -x "$PY" ] || PY="python3"

RESET=1
FILES=()
for arg in "$@"; do
  if [ "$arg" = "--no-reset" ]; then RESET=0; else FILES+=("$arg"); fi
done

# Default: the files the running feeder actually needs.
if [ "${#FILES[@]}" -eq 0 ]; then
  FILES=(main.py config.py config.json motor.py bot.py led.py wifi.py)
fi

echo "port: $ESP_PORT"
for f in "${FILES[@]}"; do
  printf '  -> %-16s ' "$f"
  "$PY" tools/espctl.py put "$f" "$f"
done

if [ "$RESET" -eq 1 ]; then
  echo -n "  -> reset           "
  "$PY" tools/espctl.py reset
fi

echo "done.  watch logs live with:  mpremote connect $ESP_PORT repl   (exit: Ctrl-])"
