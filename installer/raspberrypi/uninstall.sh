#!/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Mit sudo ausführen.' >&2; exit 1; fi
systemctl disable rampi-health.service 2>/dev/null || true
if [[ -f /opt/rampi/managed-greetd.sha256 && -f /etc/greetd/config.toml ]]; then
    expected="$(cat /opt/rampi/managed-greetd.sha256)"
    actual="$(sha256sum /etc/greetd/config.toml | cut -d ' ' -f 1)"
    if [[ "$expected" == "$actual" ]]; then
        systemctl disable greetd
        # Remove only our own default greeter route; retain the regular TTY login.
        systemctl set-default multi-user.target
    fi
fi
for path in /usr/local/bin/rampi /usr/local/bin/rampi-session /usr/local/bin/rampi-wayland-start /usr/local/bin/rampi-health /usr/share/wayland-sessions/rampi.desktop /etc/systemd/user/rampi.service /etc/systemd/system/rampi-health.service; do
    if [[ -f "$path" ]]; then rm -- "$path"; fi
done
echo 'Sitzung entfernt. Versionsstände in /opt/rampi, persönliche Daten und Systemdienste bleiben erhalten.'
