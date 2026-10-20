#!/bin/bash
set -euo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:---check}"
if [[ "$mode" != --check && "$mode" != --install && "$mode" != --image ]]; then
    echo 'Aufruf: setup.sh [--check|--install|--image]' >&2; exit 2
fi
if [[ ! -f /etc/os-release ]]; then echo 'Linux /etc/os-release fehlt.' >&2; exit 1; fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${VERSION_CODENAME:-}" != trixie || "$(dpkg --print-architecture)" != arm64 ]]; then
    echo 'Ziel: Raspberry Pi OS Lite Trixie arm64.' >&2; exit 1
fi
if [[ "$mode" != --image ]]; then
    model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
    if [[ "$model" != *'Raspberry Pi 3 Model B Plus'* && "$model" != *'Raspberry Pi 3 Model B+'* ]]; then
        echo "Nicht validierte Zielhardware: $model" >&2; exit 1
    fi
fi
packages=(python3 python3-gi gir1.2-nm-1.0 libqt6svg6 qt6-svg-plugins python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtqml
    python3-pyside6.qtquick python3-pyside6.qtquickcontrols2 python3-pyside6.qtdbus
    qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts
    qml6-module-qtquick-window qml6-module-qtquick-shapes qml6-module-qtquick-templates
    qml6-module-qtqml-workerscript xserver-xorg xinit openbox lightdm lightdm-gtk-greeter
    network-manager network-manager-gnome bluez blueman wireguard-tools
    openssh-client freerdp3-x11 xfce4-terminal chromium wmctrl arandr lxinput
    lxpolkit libsecret-tools gnome-keyring libpam-gnome-keyring unclutter-xfixes dbus-x11
    plymouth plymouth-themes plymouth-label fonts-dejavu-core accountsservice whois)
missing=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
        missing+=("$package")
    fi
done
printf 'Fehlende Pakete: %s\n' "${missing[*]:-keine}"
for service in NetworkManager bluetooth lightdm; do systemctl is-enabled "$service" || true; done
if [[ "$mode" == --check ]]; then exit 0; fi
if [[ $EUID -ne 0 ]]; then echo 'Installation mit sudo ausführen.' >&2; exit 1; fi
# Never compete with another network manager or replace a user's graphical session.
if [[ "$mode" != --image ]]; then
    for service in dhcpcd connman; do
        if systemctl is-active --quiet "$service"; then
            echo "$service ist aktiv. Netzwerk zuerst ausdrücklich auf NetworkManager migrieren." >&2; exit 1
        fi
    done
fi
if ((${#missing[@]})); then
    apt-get update
    apt-get install --no-install-recommends -y "${missing[@]}"
fi
if [[ "$mode" == --image || "${2:-}" == --with-extras ]]; then
    bash "$source_root/installer/raspberrypi/third-party.sh"
fi
install -d -m 755 /opt/rampi /usr/local/bin /usr/share/xsessions /etc/xdg/rampi /etc/systemd/user
# Versioned source trees permit rollback; the active link changes only after verification.
version="$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$source_root/client/rampi/__init__.py")"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.-]*)$ ]]; then exit 1; fi
target="/opt/rampi/$version"
install -d -m 755 "$target"
cp -a "$source_root/client/rampi" "$target/"
chmod -R a+rX "$target"
install -d -m 755 /usr/share/doc/rampi
install -m 644 "$source_root/LICENSE" /usr/share/doc/rampi/LICENSE
install -m 644 "$source_root/NOTICE" /usr/share/doc/rampi/NOTICE
install -m 644 "$source_root/assets/references/RIGHTS.md" /usr/share/doc/rampi/BRANDING-RIGHTS.md
cp -a "$source_root/docs/." /usr/share/doc/rampi/
PYTHONPATH="$target" python3 -c 'from PySide6.QtQuick import QQuickWindow; from rampi.backend import Backend'
ln -sfn "$target" /opt/rampi/current
install -m 755 "$source_root/system/rampi" /usr/local/bin/rampi
install -m 755 "$source_root/system/rampi-session" /usr/local/bin/rampi-session
install -m 644 "$source_root/system/rampi.desktop" /usr/share/xsessions/rampi.desktop
install -m 644 "$source_root/system/openbox.xml" /etc/xdg/rampi/openbox.xml
install -m 644 "$source_root/system/rampi.service" /etc/systemd/user/rampi.service
install -m 755 "$source_root/system/rampi-health" /usr/local/bin/rampi-health
install -m 644 "$source_root/system/rampi-health.service" /etc/systemd/system/rampi-health.service
install -d -m 755 /usr/share/plymouth/themes/rampi
install -m 644 "$source_root/system/plymouth/rampi.plymouth" /usr/share/plymouth/themes/rampi/
install -m 644 "$source_root/system/plymouth/rampi.script" /usr/share/plymouth/themes/rampi/
install -m 644 "$source_root/client/rampi/branding/logo.png" /usr/share/plymouth/themes/rampi/logo.png
systemctl enable NetworkManager bluetooth
if [[ "$mode" == --image ]]; then
    systemctl enable lightdm
    systemctl set-default graphical.target
    systemctl disable apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
    install -d -m 755 /etc/lightdm/lightdm.conf.d /etc/lightdm/lightdm-gtk-greeter.conf.d /usr/share/pixmaps
    install -m 644 "$source_root/system/lightdm-rampi.conf" /etc/lightdm/lightdm.conf.d/60-rampi.conf
    install -m 644 "$source_root/system/lightdm-greeter.conf" /etc/lightdm/lightdm-gtk-greeter.conf.d/60-rampi.conf
    install -m 644 "$source_root/client/rampi/branding/logo.png" /usr/share/pixmaps/rampi.png
    plymouth-set-default-theme -R rampi
    if ! grep -qw splash /boot/firmware/cmdline.txt; then
        sed -i '1 s/$/ quiet splash/' /boot/firmware/cmdline.txt
    fi
fi
echo 'Rampi installiert. Im bestehenden Login-Bildschirm die Sitzung Rampi auswählen.'
echo 'Vorhandene Login-, SSH-, Netzwerk- und Bootkonfigurationen wurden nicht überschrieben.'
