#!/bin/bash
set -euo pipefail
root="${1:-/}"
test -e "$root/usr/share/xsessions/rampi.desktop"
test -x "$root/usr/local/bin/rampi"
test -e "$root/etc/systemd/user/rampi.service"
test -e "$root/opt/rampi/current/rampi/qml/Main.qml"
test -e "$root/boot/firmware/config.txt"
test -e "$root/boot/firmware/cmdline.txt"
test -e "$root/boot/firmware/kernel8.img"
test -e "$root/boot/firmware/bcm2710-rpi-3-b-plus.dtb"
test "$(dpkg --print-architecture)" = arm64
if find "$root/opt/rampi/current" -type f -perm /002 -print -quit | grep -q .; then
    echo 'Unsichere Dateiberechtigungen.' >&2; exit 1
fi
if grep -E '^pi:[^!*:]' "$root/etc/shadow"; then
    echo 'Unerwartetes voreingestelltes Benutzerkennwort.' >&2; exit 1
fi
python3 -c 'from PySide6.QtQuick import QQuickWindow'
echo 'Rootfs-Prüfung erfolgreich. Dies ist kein Hardware-Boot-Test.'
