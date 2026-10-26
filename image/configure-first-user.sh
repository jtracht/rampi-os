#!/bin/bash
# This runs only while building a new image, never as an existing-device migration.
set -euo pipefail
if [[ $EUID != 0 || ! -d /opt/rampi-build || ! -x /usr/lib/userconf-pi/userconf-service ]]; then
    echo 'Die originale Raspberry-Pi-Ersteinrichtung im Image ist erforderlich.' >&2
    exit 1
fi
if [[ ! -f /usr/lib/systemd/system/userconfig.service && ! -f /lib/systemd/system/userconfig.service ]]; then
    echo 'Der originale userconfig-Dienst fehlt.' >&2; exit 1
fi
install -D -m 755 /opt/rampi-build/system/rampi-first-user-complete /usr/local/libexec/rampi-first-user-complete
install -D -m 644 /opt/rampi-build/system/rampi-first-user.service /etc/systemd/system/rampi-first-user.service
# Stock userconf chooses its interactive mode from the default target. A graphical
# default skips its console wizard and leaves the original pi account locked.
systemctl disable greetd.service
systemctl set-default multi-user.target
systemctl enable userconfig.service rampi-first-user.service
