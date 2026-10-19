#!/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Mit sudo ausführen.' >&2; exit 1; fi
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if command -v moonlight >/dev/null; then
    moonlight_version="$(moonlight help | sed -n 's/^Moonlight Embedded \([0-9][0-9.]*\).*/\1/p' | head -1)"
    if [[ -z "$moonlight_version" ]] || ! dpkg --compare-versions "$moonlight_version" ge 2.7.1; then
        echo 'Vorhandenes Moonlight ist nicht als kompatibles Embedded >=2.7.1 erkannt; bestehende Installation bewusst aktualisieren.' >&2
        exit 1
    fi
fi
if ! command -v tailscale >/dev/null; then
    install -d -m 755 /usr/share/keyrings
    install -m 644 "$root/installer/raspberrypi/tailscale-archive-keyring.gpg" /usr/share/keyrings/tailscale-archive-keyring.gpg
    if [[ ! -e /etc/apt/sources.list.d/tailscale.list ]]; then
        printf '%s\n' 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian trixie main' > /etc/apt/sources.list.d/tailscale.list
    fi
    apt-get update
    apt-get install --no-install-recommends -y tailscale=1.104.1
    systemctl enable tailscaled
fi
if ! command -v moonlight >/dev/null; then
    # Reuse upstream's SDL/FFmpeg/V4L2 implementation within the existing Xorg session.
    # No FKMS/firmware changes and no second display server.
    apt-get install --no-install-recommends -y git cmake build-essential pkg-config
    apt-get install --no-install-recommends -y libopus-dev libevdev-dev libudev-dev
    apt-get install --no-install-recommends -y libsdl2-dev libavcodec-dev libavutil-dev
    apt-get install --no-install-recommends -y libasound2-dev libcurl4-openssl-dev
    apt-get install --no-install-recommends -y libssl-dev libexpat1-dev libavahi-client-dev uuid-dev
    temporary="$(mktemp -d)"
    trap 'rm -rf -- "$temporary"' EXIT
    git clone https://github.com/moonlight-stream/moonlight-embedded.git "$temporary/source"
    git -C "$temporary/source" checkout --detach 775444287305849ebdf4736c75298ad0713e2d5d
    git -C "$temporary/source" submodule update --init --recursive
    cmake -S "$temporary/source" -B "$temporary/build" -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_SDL=ON -DENABLE_FFMPEG=ON -DENABLE_X11=OFF -DENABLE_CEC=OFF -DENABLE_PULSE=OFF
    cmake --build "$temporary/build" --parallel 2
    cmake --install "$temporary/build"
    ldconfig
    install -d -m 755 /usr/share/doc/rampi
    # Corresponding upstream sources, including pinned submodules, accompany the binary.
    tar --exclude=.git -czf /usr/share/doc/rampi/moonlight-embedded-2.7.1-source.tar.gz -C "$temporary" source
    install -m 644 "$temporary/source/LICENSE" /usr/share/doc/rampi/moonlight-LICENSE
fi
