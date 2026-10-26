#!/bin/bash
set -euo pipefail
export LC_ALL=C
mode="${1:---legacy}"
if [[ "$mode" != --legacy && "$mode" != --runtime-only && "$mode" != --check-runtime ]]; then
    echo 'Aufruf: third-party.sh [--runtime-only|--check-runtime]' >&2; exit 2
fi
runtime=''
if [[ "$mode" != --legacy ]]; then
    for directory in /usr/local/lib /usr/lib /usr/lib/aarch64-linux-gnu /usr/lib/arm-linux-gnueabihf /usr/lib/x86_64-linux-gnu; do
        candidate="$directory/libmoonlight-common.so.2.7.1"
        if [[ -e "$candidate" || -L "$candidate" ]]; then
            case "$(dpkg --print-architecture)" in
                arm64) machine=AArch64 ;; amd64) machine='Advanced Micro Devices X86-64' ;; armhf) machine=ARM ;;
                *) echo 'Nicht unterstützte Streaming-Architektur.' >&2; exit 1 ;;
            esac
            if ! /usr/bin/readelf -h "$candidate" | grep -Fq "${machine}"; then
                echo 'Vorhandene Streaming-Laufzeit hat eine andere Architektur; keine Überschreibung.' >&2; exit 1
            fi
            symbols="$(/usr/bin/readelf --dyn-syms --wide "$candidate")"
            for symbol in LiStartConnection LiStopConnection LiInitializeServerInformation LiSendKeyboardEvent LiSendMousePositionEvent LiGetLaunchUrlQueryParameters; do
                if ! grep -Eq "[[:space:]]${symbol}$" <<< "$symbols"; then
                    echo 'Vorhandene Moonlight-Laufzeit ist inkompatibel; sie wird nicht überschrieben.' >&2; exit 1
                fi
            done
            runtime="$candidate"; break
        fi
    done
    if [[ -n "$runtime" ]]; then printf 'Vorhandene Streaming-Laufzeit: %s\n' "$runtime"; exit 0; fi
    if [[ "$mode" == --check-runtime ]]; then echo 'Moonlight-2.7.1-Laufzeit fehlt.' >&2; exit 1; fi
fi
if [[ $EUID -ne 0 ]]; then echo 'Mit sudo ausführen.' >&2; exit 1; fi
if [[ "$mode" == --runtime-only ]]; then
    install -d -m 700 /run/rampi-install
    exec 8>/run/rampi-install/moonlight.lock
    flock -x 8
    # Another installer may have completed while waiting for this existing lock.
    if bash "${BASH_SOURCE[0]}" --check-runtime >/dev/null 2>&1; then exit 0; fi
fi
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "$mode" == --legacy ]] && command -v moonlight >/dev/null; then
    moonlight_version="$(moonlight help | sed -n 's/^Moonlight Embedded \([0-9][0-9.]*\).*/\1/p' | head -1)"
    if [[ -z "$moonlight_version" ]] || ! dpkg --compare-versions "$moonlight_version" ge 2.7.1; then
        echo 'Vorhandenes Moonlight ist nicht als kompatibles Embedded >=2.7.1 erkannt; bestehende Installation bewusst aktualisieren.' >&2
        exit 1
    fi
fi
if [[ "$mode" == --legacy ]] && ! command -v tailscale >/dev/null; then
    install -d -m 755 /usr/share/keyrings
    install -m 644 "$root/installer/raspberrypi/tailscale-archive-keyring.gpg" /usr/share/keyrings/tailscale-archive-keyring.gpg
    if [[ ! -e /etc/apt/sources.list.d/tailscale.list ]]; then
        printf '%s\n' 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian trixie main' > /etc/apt/sources.list.d/tailscale.list
    fi
    apt-get update
    apt-get install --no-install-recommends -y tailscale=1.104.1
    systemctl enable tailscaled
fi
if [[ "$mode" == --runtime-only ]] || ! command -v moonlight >/dev/null; then
    # Native mode builds only the existing official C library.
    # Legacy mode retains its existing player; no display/firmware changes.
    tools=(git cmake build-essential pkg-config libopus-dev libevdev-dev libudev-dev
        libsdl2-dev libavcodec-dev libavutil-dev libasound2-dev libcurl4-openssl-dev
        libssl-dev libexpat1-dev libavahi-client-dev uuid-dev)
    missing=()
    for package in "${tools[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then missing+=("$package"); fi
    done
    if ((${#missing[@]})); then apt-get update; apt-get install --no-install-recommends -y "${missing[@]}"; fi
    temporary="$(mktemp -d)"
    staged_library=''
    trap 'rm -f -- "${staged_library:-}"; rm -rf -- "$temporary"' EXIT
    git clone https://github.com/moonlight-stream/moonlight-embedded.git "$temporary/source"
    git -C "$temporary/source" checkout --detach 775444287305849ebdf4736c75298ad0713e2d5d
    git -C "$temporary/source" submodule update --init --recursive
    cmake -S "$temporary/source" -B "$temporary/build" -DCMAKE_BUILD_TYPE=Release \
        -DENABLE_SDL=ON -DENABLE_FFMPEG=ON -DENABLE_X11=OFF -DENABLE_CEC=OFF -DENABLE_PULSE=OFF
    if [[ "$mode" == --runtime-only ]]; then
        test "$(git -C "$temporary/source/third_party/moonlight-common-c" rev-parse HEAD)" = b126e481a195fdc7152d211def17190e3434bcce
        cmake --build "$temporary/build" --target moonlight-common --parallel 2
        destination=/usr/local/lib/libmoonlight-common.so.2.7.1
        if [[ -e "$destination" || -L "$destination" ]]; then echo 'Streaming-Laufzeit wurde während des Builds angelegt; keine Überschreibung.' >&2; exit 1; fi
        install -d -m 755 /usr/local/lib
        staged_library="$(mktemp /usr/local/lib/.rampi-moonlight.XXXXXX)"
        install -m 755 "$temporary/build/libgamestream/libmoonlight-common.so.2.7.1" "$staged_library"
        # Atomic, no-clobber publication on the same filesystem.
        ln "$staged_library" "$destination"
        rm -f -- "$staged_library"
        staged_library=''
    else
        cmake --build "$temporary/build" --parallel 2
        cmake --install "$temporary/build"
    fi
    # Native loading uses the exact absolute file; preserve existing SONAME links.
    if [[ "$mode" == --legacy ]]; then ldconfig; fi
    install -d -m 755 /usr/share/doc/rampi
    # Inventory actual tracked files, including every pinned submodule.
    (cd "$temporary/source"; git ls-files --recurse-submodules -z | xargs -0 sha256sum --) > /usr/share/doc/rampi/moonlight-source-files.sha256
    # Corresponding upstream sources, including pinned submodules, accompany the binary.
    tar --exclude=.git -czf /usr/share/doc/rampi/moonlight-embedded-2.7.1-source.tar.gz -C "$temporary" source
    install -m 644 "$temporary/source/LICENSE" /usr/share/doc/rampi/moonlight-LICENSE
    if [[ "$mode" == --runtime-only ]]; then
        sha256sum "$destination" > /usr/share/doc/rampi/moonlight-runtime.sha256
        printf '%s\n' 'embedded=775444287305849ebdf4736c75298ad0713e2d5d' 'common=b126e481a195fdc7152d211def17190e3434bcce' > /usr/share/doc/rampi/moonlight-source-revisions.txt
    fi
fi
