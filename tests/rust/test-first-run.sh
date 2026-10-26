#!/bin/bash
# Observe the ordinary first launch with real Wayland keyboard input, no app test hook.
set -euo pipefail
if [[ "${RAMPI_TEST_CONTAINER:-}" != 1 || ! -f /.dockerenv || "$XDG_CONFIG_HOME" != /tmp/rampi-wayland.*/config ]]; then exit 2; fi
settings="$XDG_CONFIG_HOME/rampi/settings.json"
test ! -e "$settings"
log="$(mktemp /tmp/rampi-first-run.XXXXXX)"
application_pid=''
stop_application() {
    if [[ -n "$application_pid" ]]; then
        kill "$application_pid" 2>/dev/null || true
        wait "$application_pid" 2>/dev/null || true
        application_pid=''
    fi
}
trap 'stop_application; rm -f -- "$log"' EXIT
start_application() {
    /build/target/debug/rampi-native > "$log" 2>&1 &
    application_pid=$!
    # Send input once, after the actual cold GTK toplevel is mapped.
    for _ in $(seq 1 100); do
        if wlrctl toplevel list | grep -Fq 'org.rampi.Workstation'; then return 0; fi
        if ! kill -0 "$application_pid" 2>/dev/null; then cat "$log"; return 1; fi
        sleep 0.1
    done
    cat "$log"; echo 'First-run window did not map.' >&2; return 1
}
start_application
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
stop_application
python3 - "$settings" <<'PY'
import json, sys
with open(sys.argv[1], 'w') as target:
    json.dump({'setup_step': 11, 'hosts': [{'address': 'host.example', 'username': 'fixture',
        'project': 'existing-personal-project'}]}, target)
PY
start_application
# Published ID 11 means Streaming. Its next retained step is RDP (ID 12),
# rather than the finish/later action at new display position 11.
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    grim "$RAMPI_TEST_ARTIFACTS/rust-setup-published-resume.png"
    chmod 644 "$RAMPI_TEST_ARTIFACTS/rust-setup-published-resume.png"
fi
wtype -s 150 -k Tab -s 100 -k Tab -s 100 -k Return
for _ in $(seq 1 100); do
    if python3 - "$settings" <<'PY'
import json, sys
sys.exit(0 if json.load(open(sys.argv[1]))['setup_step'] == 12 else 1)
PY
    then break; fi
    sleep 0.03
done
python3 - "$settings" <<'PY'
import json, sys
settings = json.load(open(sys.argv[1]))
assert settings['setup_step'] == 12 and not settings['setup_complete']
assert settings['hosts'][0]['project'] == 'existing-personal-project'
print('RAMPI_RUST_SETUP_PUBLISHED_RESUME_OK')
PY
stop_application
rm -- "$settings"
printf '%s\n' '{"language":"en","setup_complete":true}' > "$settings"
timeout 30 /build/target/debug/rampi-native --language-ui-check
rm -- "$settings"
