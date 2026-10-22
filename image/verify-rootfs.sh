#!/bin/bash
set -euo pipefail
root="${1:-/}"
test -e "$root/usr/share/wayland-sessions/rampi.desktop"
test -x "$root/usr/local/bin/rampi"
test -e "$root/etc/systemd/user/rampi.service"
test -e "$root/etc/xdg/rampi/labwc/rc.xml"
test -x "$root/opt/rampi/current/rampi-native"
test -e "$root/boot/firmware/config.txt"
test -e "$root/boot/firmware/cmdline.txt"
test -e "$root/boot/firmware/kernel8.img"
test -e "$root/boot/firmware/bcm2710-rpi-3-b-plus.dtb"
test "$(dpkg --print-architecture)" = arm64
if find -L "$root/opt/rampi/current" "$root/opt/rampi/current/assets" \( -perm /022 -o ! -uid 0 -o ! -gid 0 \) -print -quit | grep -q .; then
    echo 'Programmdateien müssen root gehören und für andere Benutzer schreibgeschützt sein.' >&2; exit 1
fi
if grep -qE '^pi:[^!*:]' "$root/etc/shadow"; then
    echo 'Unerwartetes voreingestelltes Benutzerkennwort.' >&2; exit 1
fi
# Runtime probes must run inside the image, not resolve host libraries against a prefix.
test "$root" = /
/usr/local/bin/rampi-health
expected="$(cat /opt/rampi/binary-sha256.txt)"
[[ "$expected" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$expected" /opt/rampi/current/rampi-native | sha256sum --check --status
if grep -Eq 'startx|Xorg|xinit' /usr/local/bin/rampi-session /etc/systemd/user/rampi.service; then
    echo 'Alte X11-Sitzung im nativen Image gefunden.' >&2; exit 1
fi
echo 'RAMPI_NATIVE_ROOTFS_OK: Rust-Binary, Laufzeitbibliotheken, Wayland-Sitzung und Dateirechte geprüft.'
echo 'Dies ist kein grafischer Login- oder Hardware-Boot-Test.'
