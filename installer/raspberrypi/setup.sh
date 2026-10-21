#!/bin/bash
set -euo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:---check}"
if [[ "$mode" != --check && "$mode" != --install && "$mode" != --image ]]; then echo 'Aufruf: setup.sh [--check|--install|--image]' >&2; exit 2; fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${VERSION_CODENAME:-}" != trixie || "$(dpkg --print-architecture)" != arm64 ]]; then echo 'Ziel: Raspberry Pi OS Lite Trixie arm64.' >&2; exit 1; fi
if [[ "$mode" != --image ]]; then
    model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
    if [[ "$model" != *'Raspberry Pi 3 Model B Plus'* && "$model" != *'Raspberry Pi 3 Model B+'* ]]; then echo "Nicht validierte Zielhardware: $model" >&2; exit 1; fi
fi
packages=(libgtk-4-1 libvte-2.91-gtk4-0 libwebkitgtk-6.0-4 libgtk-4-media-gstreamer librsvg2-common
    gstreamer1.0-plugins-good gstreamer1.0-pulseaudio libcanberra0 libcanberra-pulse labwc greetd wlgreet dbus-user-session
    network-manager libnm0 bluez wireguard-tools openssh-client freerdp3-wayland
    wlr-randr libsecret-tools gnome-keyring libpam-gnome-keyring
    plymouth plymouth-themes fonts-dejavu-core accountsservice whois binutils)
if ! dpkg-query -W -f='${Status}' pulseaudio 2>/dev/null | grep -q '^install ok installed$'; then
    packages+=(pipewire-audio)
fi
new_login=0
if [[ "$mode" == --image ]] || [[ ! -e /etc/greetd/config.toml && ! -e /etc/systemd/system/display-manager.service ]]; then new_login=1; fi
if [[ "$mode" != --image && -e /etc/systemd/system/display-manager.service ]]; then
    existing="$(readlink -f /etc/systemd/system/display-manager.service)"
    if [[ "$existing" != */greetd.service ]]; then
        reused=()
        for package in "${packages[@]}"; do
            if [[ "$package" != greetd && "$package" != wlgreet ]]; then reused+=("$package"); fi
        done
        packages=("${reused[@]}")
        printf 'Vorhandener Login-Dienst bleibt erhalten: %s\n' "$existing"
    fi
fi
missing=()
for package in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then missing+=("$package"); fi
done
printf 'Fehlende Wayland-Pakete: %s\n' "${missing[*]:-keine}"
binary="${RAMPI_NATIVE_BINARY:-$source_root/native/bin/rampi-native}"
if [[ ! -x "$binary" ]]; then echo 'ARM64-Rust-Binary fehlt. CI-Artefakt als native/bin/rampi-native bereitstellen.' >&2; exit 1; fi
if [[ "$mode" == --check ]]; then exit 0; fi
if [[ $EUID -ne 0 ]]; then echo 'Installation mit sudo ausführen.' >&2; exit 1; fi
if [[ "$mode" != --image ]]; then
    for service in dhcpcd connman; do
        if systemctl is-active --quiet "$service"; then echo "$service ist aktiv; Netzwerk zuerst auf NetworkManager migrieren." >&2; exit 1; fi
    done
fi
if ((${#missing[@]})); then apt-get update; apt-get install --no-install-recommends -y "${missing[@]}"; fi
if ! readelf -h "$binary" | grep -q 'AArch64'; then echo 'Kein ARM64-Binary.' >&2; exit 1; fi
version="$("$binary" --version | sed -n 's/^Rampi \([^ ]*\).*/\1/p')"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.-]*)$ ]]; then echo 'Ungültige Binary-Version.' >&2; exit 1; fi
target="/opt/rampi/$version"
install -d -m 755 "$target" /usr/local/bin /usr/share/wayland-sessions /etc/xdg/rampi/labwc /etc/systemd/user /usr/share/rampi
install -m 755 "$binary" "$target/rampi-native"
"$target/rampi-native" --version
cp -a "$source_root/client/rampi/branding" "$source_root/client/rampi/icons" "$source_root/client/rampi/sounds" /usr/share/rampi/
chown -hR root:root "$target" /usr/share/rampi
chmod -R a+rX,go-w "$target" /usr/share/rampi
for name in rampi rampi-session rampi-wayland-start rampi-health; do install -m 755 "$source_root/system/$name" "/usr/local/bin/$name"; done
install -m 644 "$source_root/system/rampi.desktop" /usr/share/wayland-sessions/rampi.desktop
install -m 644 "$source_root/system/rampi.service" /etc/systemd/user/rampi.service
install -m 644 "$source_root/system/labwc/rc.xml" /etc/xdg/rampi/labwc/rc.xml
install -m 644 "$source_root/system/rampi-health.service" /etc/systemd/system/rampi-health.service
install -d -m 755 /usr/share/doc/rampi
cp -a "$source_root/docs/." /usr/share/doc/rampi/
install -m 644 "$source_root/LICENSE" "$source_root/NOTICE" /usr/share/doc/rampi/
ln -sfn "$target" /opt/rampi/current
systemctl enable NetworkManager bluetooth
if [[ "$new_login" == 1 ]]; then
    install -d -m 755 /etc/greetd /etc/xdg/rampi/greeter
    install -m 644 "$source_root/system/greetd.toml" /etc/greetd/config.toml
    install -m 644 "$source_root/system/labwc/rc.xml" /etc/xdg/rampi/greeter/rc.xml
    systemctl enable greetd
    systemctl set-default graphical.target
fi
if [[ "$mode" == --image ]]; then
    systemctl disable apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
fi
echo 'Rust-/Wayland-Sitzung installiert. Vorhandene Login-Konfigurationen bleiben außerhalb des Image-Builds erhalten. Updates sind manuell.'
