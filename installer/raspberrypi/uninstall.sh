#!/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Mit sudo ausführen.' >&2; exit 1; fi
for path in /usr/local/bin/rampi /usr/local/bin/rampi-session /usr/share/xsessions/rampi.desktop /etc/systemd/user/rampi.service; do
    if [[ -f "$path" ]]; then rm -- "$path"; fi
done
echo 'Sitzung entfernt. Versionsstände in /opt/rampi, persönliche Daten und Systemdienste bleiben erhalten.'
