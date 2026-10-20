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
printf '<labwc_config/>\n' > "$test_home/compositor/rc.xml"
labwc -C "$test_home/compositor" > "$test_home/compositor.log" 2>&1 &
compositor_pid=$!
trap 'kill "$compositor_pid" 2>/dev/null || true' EXIT
for _ in $(seq 1 100); do
    [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] && break
    sleep 0.1
done
if [[ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]]; then cat "$test_home/compositor.log"; exit 1; fi
/build/target/debug/rampi-native --self-test &
application_pid=$!
if [[ -n "${RAMPI_TEST_ARTIFACTS:-}" ]]; then
    sleep 0.5
    grim "$RAMPI_TEST_ARTIFACTS/rust-wayland-dashboard.png"
fi
wait "$application_pid"
/build/target/debug/rampi-native --embedded-test
if pgrep -x Xorg || pgrep -x Xwayland || pgrep -x startx; then echo 'Unerlaubter X11-Prozess.' >&2; exit 1; fi
echo RAMPI_WAYLAND_WITHOUT_X11_OK
