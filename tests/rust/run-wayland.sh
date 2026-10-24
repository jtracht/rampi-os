#!/bin/bash
set -euo pipefail
umask 077
if [[ "${RAMPI_TEST_CONTAINER:-}" != 1 ]]; then echo 'Nur im isolierten Testcontainer ausführen.' >&2; exit 2; fi
if [[ -n "${DISPLAY:-}" ]]; then echo 'Der Test darf keinen X11-Server verwenden.' >&2; exit 1; fi
test_home="$(mktemp -d /tmp/rampi-wayland.XXXXXX)"
export HOME="$test_home/home" XDG_RUNTIME_DIR="$test_home/runtime" XDG_CONFIG_HOME="$test_home/config" XDG_CACHE_HOME="$test_home/cache"
mkdir -p "$HOME" "$XDG_RUNTIME_DIR" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
export WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_HEADLESS_OUTPUTS=1
export GDK_BACKEND=wayland GSK_RENDERER=cairo RAMPI_ASSETS=/src/client/rampi
export WAYLAND_DISPLAY=wayland-0 GTK_A11Y=none
mkdir "$test_home/compositor"
cp /src/system/labwc/rc.xml "$test_home/compositor/rc.xml"
# The installed launcher resolves the selected release. In this container it is
# replaced only in the temporary config by the actual development binary.
sed -i 's@/usr/local/bin/rampi@/build/target/debug/rampi-native@g' "$test_home/compositor/rc.xml"
mkdir -p "$XDG_CONFIG_HOME/rampi/labwc"
labwc -C "$XDG_CONFIG_HOME/rampi/labwc" -c "$test_home/compositor/rc.xml" > "$test_home/compositor.log" 2>&1 &
compositor_pid=$!
export LABWC_PID="$compositor_pid"
trap 'kill "$compositor_pid" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do
    [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] && break
    sleep 0.1
done
if [[ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]]; then cat "$test_home/compositor.log"; exit 1; fi
bash tests/rust/test-first-run.sh
/build/target/debug/rampi-native --self-test > "$test_home/application.log" 2>&1 &
application_pid=$!
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    sleep 0.5
    grim "$RAMPI_TEST_ARTIFACTS/rust-wayland-dashboard.png"
    chmod 644 "$RAMPI_TEST_ARTIFACTS/rust-wayland-dashboard.png"
fi
wait "$application_pid" || { cat "$test_home/application.log"; exit 1; }
cat "$test_home/application.log"
if grep -q 'Gtk-WARNING' "$test_home/application.log"; then echo 'GTK layout warning in the actual interface.' >&2; exit 1; fi
/build/target/debug/rampi-native --keyboard-test &
keyboard_pid=$!
sleep 0.4
wtype -s 150 -k Right -s 100 -k Left -s 100 -k Return
sleep 1.2
wtype -s 150 -k Escape
wait "$keyboard_pid"
python3 tests/rust/test-dashboard.py
python3 tests/rust/test-ssh-setup.py
python3 tests/rust/test-ai-pages.py
timeout 20 /build/target/debug/rampi-native --setup-ui-check
timeout 40 /build/target/debug/rampi-native --system-ui-check
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    timeout 45 /build/target/debug/rampi-native --interaction-check > "$test_home/interaction.log" 2>&1 || { cat "$test_home/interaction.log"; exit 1; }
    cat "$test_home/interaction.log"
    if grep -qE 'Gtk-WARNING|CRITICAL' "$test_home/interaction.log"; then exit 1; fi
    python3 tests/rust/check-visual.py
fi
/build/target/debug/rampi-native --embedded-test
python3 tests/rust/test-bluetooth.py --ui
python3 tests/rust/test-pairing.py
python3 tests/rust/test-wireguard.py --ui
python3 tests/rust/test-tailscale.py --ui
python3 - "$HOME/rampi-board-test.json" <<'PY'
import json, sys
with open(sys.argv[1], 'w') as target:
    json.dump({'title': 'Rust Kanban fixture', 'cards': [
        {'title': 'Alpha VPN', 'project': 'Infra', 'priority': 'high', 'status': 'Review'},
        {'title': 'Beta Layout', 'project': 'UI', 'priority': 'low', 'status': 'Offen'},
        {'title': 'Gamma VPN', 'project': 'Infra', 'priority': 'low', 'status': 'Offen'},
    ]}, target)
PY
timeout 20 /build/target/debug/rampi-native --board-ui-check
pulseaudio --start --exit-idle-time=-1 --log-target="file:$test_home/audio.log"
export PULSE_SINK=rampi_feedback
pactl load-module module-null-sink sink_name=rampi_feedback >/dev/null
pactl set-default-sink rampi_feedback
pactl set-sink-volume rampi_feedback 100%
pactl set-source-volume rampi_feedback.monitor 100%
parec --device=rampi_feedback.monitor --format=s16le --rate=48000 --channels=1 --latency-msec=20 > "$test_home/click.pcm" &
record_pid=$!
timeout 15 /build/target/debug/rampi-native --sound-test
sleep 0.6
kill "$record_pid"
wait "$record_pid" 2>/dev/null || true
python3 - "$test_home/click.pcm" <<'PY'
import array, sys
data = array.array('h')
data.frombytes(open(sys.argv[1], 'rb').read())
peak=max(map(abs,data),default=0)
if len(data) < 1000 or peak < 50:
    raise SystemExit(f'Actual native click playback is silent or too quiet: peak={peak}')
print(f'RAMPI_RUST_SOUND_PCM_OK peak={peak}')
PY
timeout 240 /build/target/debug/rampi-native --performance-test
if pgrep -x Xorg || pgrep -x Xwayland || pgrep -x startx; then echo 'Unerlaubter X11-Prozess.' >&2; exit 1; fi
echo RAMPI_WAYLAND_WITHOUT_X11_OK
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    cat /sys/fs/cgroup/memory.peak > "$RAMPI_TEST_ARTIFACTS/memory-peak-bytes.txt"
    chmod 644 "$RAMPI_TEST_ARTIFACTS/memory-peak-bytes.txt"
fi
