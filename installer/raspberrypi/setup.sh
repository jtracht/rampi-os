#!/bin/bash
set -euo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="${1:---check}"
if [[ "$mode" == --repair ]]; then mode=--install; fi
if [[ "$mode" != --check && "$mode" != --install && "$mode" != --image ]]; then echo 'Aufruf: setup.sh [--check|--install|--repair|--image]' >&2; exit 2; fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${VERSION_CODENAME:-}" != trixie || "$(dpkg --print-architecture)" != arm64 ]]; then echo 'Ziel: Raspberry Pi OS Lite Trixie arm64.' >&2; exit 1; fi
if [[ "$mode" != --image ]]; then
    model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
    if [[ "$model" != *'Raspberry Pi 3 Model B Plus'* && "$model" != *'Raspberry Pi 3 Model B+'* ]]; then echo "Nicht validierte Zielhardware: $model" >&2; exit 1; fi
fi
packages=(libgtk-4-1 libvte-2.91-gtk4-0 libwebkitgtk-6.0-4 libgtk-4-media-gstreamer librsvg2-common
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav libcurl4t64 gstreamer1.0-pulseaudio libcanberra0 libcanberra-pulse labwc greetd wlgreet dbus-user-session
    network-manager libnm0 bluez wireguard-tools openssh-client libgstreamer-plugins-base1.0-0 libssl3t64
    libusbredirparser1t64 libusb-1.0-0
    wlr-randr libsecret-tools gnome-keyring libpam-gnome-keyring curl
    plymouth plymouth-themes fonts-dejavu-core accountsservice whois binutils sudo passwd)
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
# Inspect the fixed ELF header with Coreutils before installing dependencies.
# A fresh Lite system need not have the optional binutils/readelf package yet.
header="$(od -An -N64 -tx1 "$binary" | tr -d '[:space:]')"
if [[ ${#header} -ne 128 || "$header" != 7f454c46020101* || "${header:36:4}" != b700 || "${header:40:8}" != 01000000 || "${header:104:4}" != 4000 ]]; then
    echo 'Kein vollständiger ARM64-ELF-Header.' >&2; exit 1
fi
if [[ -f "$source_root/native/bin/binary-sha256.txt" ]]; then
    expected="$(cat "$source_root/native/bin/binary-sha256.txt")"
    [[ "$expected" =~ ^[a-f0-9]{64}$ ]]
    printf '%s  %s\n' "$expected" "$binary" | sha256sum --check --status
fi
if [[ "$mode" == --check ]]; then exit 0; fi
if [[ $EUID -ne 0 ]]; then echo 'Installation mit sudo ausführen.' >&2; exit 1; fi
if [[ "$mode" != --image ]]; then
    for service in dhcpcd connman; do
        if systemctl is-active --quiet "$service"; then echo "$service ist aktiv; Netzwerk zuerst auf NetworkManager migrieren." >&2; exit 1; fi
    done
fi
if ((${#missing[@]})); then apt-get update; apt-get install --no-install-recommends -y "${missing[@]}"; fi
version="$("$binary" --version | sed -n 's/^Rampi \([^ ]*\).*/\1/p')"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.-]*)$ ]]; then echo 'Ungültige Binary-Version.' >&2; exit 1; fi
# Serialize manual installs; prepare a complete version before activating it.
install -d -m 755 /opt/rampi
install -d -m 700 /run/rampi-install
exec 9>/run/rampi-install/lock
flock -x 9
# Reuse a compatible existing library; otherwise build only upstream Moonlight C.
bash "$source_root/installer/raspberrypi/third-party.sh" --runtime-only
fingerprint="$(sha256sum "$binary" | cut -d ' ' -f 1)"
assets_hash="$(find "$source_root/client/rampi/branding" "$source_root/client/rampi/icons" "$source_root/client/rampi/sounds" -type f -print0 | sort -z | xargs -0 sha256sum | awk '{print $1}' | sha256sum | cut -d ' ' -f 1)"
target="/opt/rampi/$version-${fingerprint:0:12}-${assets_hash:0:12}"
staging="$(mktemp -d /opt/rampi/.stage.XXXXXX)"
trap 'rm -rf -- "$staging"' EXIT
install -m 755 "$binary" "$staging/rampi-native"
install -d -m 755 "$staging/assets"
cp -a "$source_root/client/rampi/branding" "$source_root/client/rampi/icons" "$source_root/client/rampi/sounds" "$staging/assets/"
printf '%s  rampi-native\n' "$fingerprint" > "$staging/SHA256SUMS"
"$staging/rampi-native" --version
chown -hR root:root "$staging"
chmod -R a+rX,go-w "$staging"
# A repeat install repairs an existing version by replacing its inactive directory.
# Never overwrite a running executable in place.
if [[ -e "$target" ]]; then
    replacement="$(mktemp -d "${target}.repair.XXXXXX")"
    rmdir -- "$replacement"
    mv -- "$staging" "$replacement"
    staging="$(mktemp -d /opt/rampi/.stage.XXXXXX)"
    target="$replacement"
else
    mv -- "$staging" "$target"
    staging="$(mktemp -d /opt/rampi/.stage.XXXXXX)"
fi
install -d -m 755 /usr/local/bin /usr/share/wayland-sessions /etc/xdg/rampi/labwc /etc/systemd/user
for name in rampi rampi-session rampi-wayland-start rampi-health rampi-greeter; do install -m 755 "$source_root/system/$name" "/usr/local/bin/$name"; done
install -m 644 "$source_root/system/rampi.desktop" /usr/share/wayland-sessions/rampi.desktop
install -m 644 "$source_root/system/rampi.service" /etc/systemd/user/rampi.service
bash "$source_root/installer/raspberrypi/keyring-profile.sh" --install
install -m 644 "$source_root/system/labwc/rc.xml" /etc/xdg/rampi/labwc/rc.xml
install -m 644 "$source_root/system/rampi-health.service" /etc/systemd/system/rampi-health.service
install -d -m 755 /usr/share/doc/rampi
cp -a "$source_root/docs/." /usr/share/doc/rampi/
install -m 644 "$source_root/LICENSE" "$source_root/NOTICE" /usr/share/doc/rampi/
if [[ -d "$source_root/native/bin/rust-licenses" ]]; then
    cp -a "$source_root/native/bin/rust-licenses" /usr/share/doc/rampi/
    chown -hR root:root /usr/share/doc/rampi/rust-licenses
    chmod -R a+rX,go-w /usr/share/doc/rampi/rust-licenses
fi
systemctl enable NetworkManager bluetooth
if [[ "$new_login" == 1 ]]; then
    install -d -m 755 /etc/greetd /etc/xdg/rampi/greeter
    install -m 644 "$source_root/system/greetd.toml" /etc/greetd/config.toml
    sha256sum /etc/greetd/config.toml | cut -d ' ' -f 1 > /opt/rampi/managed-greetd.sha256
    install -m 644 "$source_root/system/labwc/greeter.xml" /etc/xdg/rampi/greeter/rc.xml
    install -m 644 "$source_root/system/wlgreet.toml" /etc/xdg/rampi/greeter/wlgreet.toml
    systemctl enable greetd
    systemctl set-default graphical.target
else
    # shellcheck disable=SC1091
    source "$source_root/installer/raspberrypi/greeter-profile.sh"
    rampi_migrate_greeter_profile "$source_root" /etc/greetd/config.toml /opt/rampi/managed-greetd.sha256 /etc/xdg/rampi/greeter/rc.xml
    rampi_migrate_greeter_branding "$source_root" /etc/greetd/config.toml /opt/rampi/managed-greetd.sha256 /etc/xdg/rampi/greeter/rc.xml /etc/xdg/rampi/greeter/wlgreet.toml
fi
if [[ "$mode" == --image ]]; then
    systemctl disable apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
fi
previous="$(readlink -f /opt/rampi/current || true)"
if [[ "$previous" == /opt/rampi/* && "$previous" != "$target" && -x "$previous/rampi-native" ]]; then
    ln -s "$previous" "$staging/previous"
    mv -Tf "$staging/previous" /opt/rampi/previous
fi
ln -s "$target" "$staging/current"
mv -Tf "$staging/current" /opt/rampi/current

echo 'Rust-/Wayland-Sitzung installiert. Vorhandene Login-Konfigurationen bleiben außerhalb des Image-Builds erhalten. Updates sind manuell.'
