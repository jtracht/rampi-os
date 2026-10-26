#!/bin/bash
set -euo pipefail
test "${RAMPI_TEST_CONTAINER:-}" = 1
test -f /.dockerenv
umask 077
export PULSE_SERVER="unix:${XDG_RUNTIME_DIR}/pulse/native"
root=$(mktemp -d /tmp/rampi-stream-ui.XXXXXX)
export HOME="$root/home" XDG_CONFIG_HOME="$root/config" XDG_CACHE_HOME="$root/cache" XDG_RUNTIME_DIR="$root/runtime"
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
export WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_HEADLESS_OUTPUTS=1
export GDK_BACKEND=wayland GSK_RENDERER=cairo WAYLAND_DISPLAY=wayland-0 GTK_A11Y=none RAMPI_ASSETS=/src/client/rampi
test -z "${DISPLAY:-}"
mkdir -p "$root/compositor"
cp system/labwc/rc.xml "$root/compositor/rc.xml"
# The installed launcher is replaced only inside this disposable compositor config.
sed -i 's@/usr/local/bin/rampi@/build/target/debug/rampi-native@g' "$root/compositor/rc.xml"
labwc -C "$root/compositor" > "$root/compositor.log" 2>&1 &
compositor=$!
trap 'kill "$compositor" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do
    test ! -S "$XDG_RUNTIME_DIR/wayland-0" || break
    sleep 0.1
done
test -S "$XDG_RUNTIME_DIR/wayland-0"
# Fixture-only keyring; actual installed-image PAM remains a separate required test.
printf '%s' fixture-only | gnome-keyring-daemon --unlock --components=secrets > "$root/keyring.log"
args=(--stream-ui-check)
if [[ "${RAMPI_TEST_STREAM_SOAK:-}" == 1 ]]; then args+=(--stream-ui-soak); fi
timeout 1100 /build/target/debug/rampi-native "${args[@]}"
test -z "$(pgrep -x Xwayland || true)"
