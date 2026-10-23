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
bundle="rampi-linux-arm64-$version.tar.xz"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT
url="https://github.com/jtracht/rampi-os/releases/download/v$version"
# Download only on explicit invocation; never register a timer or background updater.
curl --disable --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 300 --max-filesize 1073741824 -fsSL "$url/SHA256SUMS" -o "$temporary/SHA256SUMS"
for artifact in "$archive" "$bundle"; do
    curl --disable --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 300 --max-filesize 1073741824 -fsSL "$url/$artifact" -o "$temporary/$artifact"
    checksum="$(awk -v file="$artifact" '$2 == file {print $1}' "$temporary/SHA256SUMS")"
    [[ "$checksum" =~ ^[a-f0-9]{64}$ ]] || { echo 'Eindeutige Prüfsumme fehlt.' >&2; exit 1; }
    (cd "$temporary"; printf '%s  %s\n' "$checksum" "$artifact" | sha256sum --check --status)
done
python3 - "$temporary" "$archive" "$bundle" <<'PY'
import hashlib
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath
root = Path(sys.argv[1])
for filename, destination, prefix in [
    (sys.argv[2], root, "rampi-os"),
    (sys.argv[3], root / "rampi-os/native", "bin"),
]:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(root / filename) as archive:
        members = archive.getmembers()
        if len(members) > 30000 or sum(m.size for m in members) > 1024**3:
            raise SystemExit("Releasearchiv überschreitet das Limit")
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (not path.parts or path.is_absolute() or path.parts[0] != prefix
                or ".." in path.parts or "\\" in member.name
                or not (member.isfile() or member.isdir()) or path in seen):
                raise SystemExit("Unsicherer oder doppelter Release-Archiveintrag")
            seen.add(path)
        archive.extractall(destination, members=members, filter="data")
source = root / "rampi-os"
native = source / "native/bin"
revision = (source / "source-revision.txt").read_text().strip()
if not re.fullmatch("[a-f0-9]{40}", revision) or revision != (native / "source-revision.txt").read_text().strip():
    raise SystemExit("Quellcode und ARM64-Paket gehören nicht zum selben Stand")
expected = (native / "binary-sha256.txt").read_text().strip()
if not re.fullmatch("[a-f0-9]{64}", expected) or hashlib.sha256((native / "rampi-native").read_bytes()).hexdigest() != expected:
    raise SystemExit("ARM64-Binary-Prüfsumme stimmt nicht")
PY
bash "$temporary/rampi-os/installer/raspberrypi/setup.sh" "$@"
