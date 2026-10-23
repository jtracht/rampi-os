#!/bin/bash
# Observe the ordinary first launch with real Wayland keyboard input, no app test hook.
set -euo pipefail
if [[ "${RAMPI_TEST_CONTAINER:-}" != 1 || ! -f /.dockerenv || "$XDG_CONFIG_HOME" != /tmp/rampi-wayland.*/config ]]; then exit 2; fi
settings="$XDG_CONFIG_HOME/rampi/settings.json"
test ! -e "$settings"
log="$(mktemp /tmp/rampi-first-run.XXXXXX)"
/build/target/debug/rampi-native > "$log" 2>&1 &
application_pid=$!
trap 'kill "$application_pid" 2>/dev/null || true; wait "$application_pid" 2>/dev/null || true; rm -f -- "$log"' EXIT
sleep 0.7
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    grim "$RAMPI_TEST_ARTIFACTS/rust-first-run.png"
    chmod 644 "$RAMPI_TEST_ARTIFACTS/rust-first-run.png"
fi
# GTK initially focuses the first enabled action. Tab selects Next; Enter saves it.
wtype -s 150 -k Tab -s 100 -k Return
for _ in $(seq 1 100); do
    [[ -f "$settings" ]] && break
    sleep 0.03
done
if [[ ! -f "$settings" ]]; then cat "$log"; exit 1; fi
python3 - "$settings" <<'PY'
import json, sys
settings = json.load(open(sys.argv[1]))
assert settings['setup_step'] == 1 and not settings['setup_complete']
print('RAMPI_RUST_FIRST_RUN_KEYBOARD_OK')
PY
kill "$application_pid"
wait "$application_pid" 2>/dev/null || true
rm -- "$settings"
