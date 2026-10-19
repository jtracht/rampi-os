#!/bin/bash
set -uo pipefail
uname -a
cat /etc/os-release
free -m
df -h /
for name in nmcli bluetoothctl tailscale wg ssh xfreerdp3 moonlight chromium xfce4-terminal; do
    command -v "$name" || true
done
systemctl --no-pager --full status NetworkManager bluetooth lightdm || true
systemctl --user --no-pager --full status rampi || true
if command -v vcgencmd >/dev/null; then vcgencmd get_throttled; vcgencmd measure_temp; fi
echo 'Netzwerkdetails, private Schlüssel und Authentifizierungstoken werden nicht ausgegeben.'
