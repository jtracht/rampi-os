#!/bin/bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$root/installer/raspberrypi/setup.sh" ]]; then
    exec bash "$root/installer/raspberrypi/setup.sh" "$@"
fi
# Release packaging updates this marker; invocation remains an explicit manual install.
RAMPI_BOOTSTRAP_VERSION='0.1.0.dev0'
version="${RAMPI_VERSION:-$RAMPI_BOOTSTRAP_VERSION}"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.-]*)$ ]]; then
    echo 'Ungültige Releaseversion.' >&2; exit 2
fi
archive="rampi-source-$version.tar.gz"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT
url="https://github.com/jtracht/rampi-os/releases/download/v$version"
curl --proto '=https' --tlsv1.2 -fsSL "$url/$archive" -o "$temporary/$archive"
curl --proto '=https' --tlsv1.2 -fsSL "$url/SHA256SUMS" -o "$temporary/SHA256SUMS"
checksum="$(awk -v file="$archive" '$2 == file {print $1}' "$temporary/SHA256SUMS")"
[[ "$checksum" =~ ^[a-f0-9]{64}$ ]] || { echo 'Prüfsumme fehlt.' >&2; exit 1; }
(cd "$temporary"; printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status)
tar --extract --gzip --no-same-owner --no-same-permissions -f "$temporary/$archive" -C "$temporary"
bash "$temporary/rampi-os/installer/raspberrypi/setup.sh" "$@"
