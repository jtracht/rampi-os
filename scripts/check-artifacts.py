"""Verify the shipped archives and every checksum before publication."""

import argparse
import hashlib
import re
import tarfile
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--image", action="store_true")
args = parser.parse_args()
directory = args.directory
required = {"setup.sh", "setup.ps1", "LICENSE", "NOTICE"}
version = re.search(
    r'__version__ = "([^"]+)"',
    (Path(__file__).resolve().parents[1] / "client/rampi/__init__.py").read_text(),
).group(1)
source = f"rampi-source-{version}.tar.gz"
host = f"rampi-windows-host-{version}.zip"
required.update([source, host])
if args.image:
    images = list(directory.glob("*.img.xz"))
    if len(images) != 1:
        raise SystemExit("Exactly one flashable image required")
    required.update([
        images[0].name, "package-manifest.tsv", "dependency-licenses.tar.xz",
        "qemu-boot.log", "qemu-environment.txt", "partitions.json",
        "pi-gen-revision.txt", "readiness.json",
    ])
checksums = {}
for line in (directory / "SHA256SUMS").read_text().splitlines():
    digest, name = line.split("  ", 1)
    if Path(name).name != name or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise SystemExit("Invalid checksum manifest entry")
    if name in checksums or name == "SHA256SUMS":
        raise SystemExit("Duplicate or self-referential checksum entry")
    checksums[name] = digest
if not required.issubset(checksums):
    raise SystemExit("Required release files missing from checksum manifest")
for name, expected in checksums.items():
    with (directory / name).open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected != actual:
        raise SystemExit(f"Checksum mismatch: {name}")
with tarfile.open(directory / source) as archive:
    entries = set(archive.getnames())
    for name in [
        ".github/workflows/ci.yml", ".github/workflows/release.yml", "LICENSE",
        "client/rampi/qml/Main.qml", "client/rampi/icons/LICENSE", "image/build.sh",
        "installer/raspberrypi/setup.sh", "docs/INSTALL-RASPBERRYPI.md", "setup.sh",
    ]:
        if "rampi-os/" + name not in entries:
            raise SystemExit(f"Source archive incomplete: {name}")
with zipfile.ZipFile(directory / host) as archive:
    for name in ["setup.ps1", "installer/windows/setup.ps1", "host/windows/rampi-session.ps1"]:
        if name not in archive.namelist():
            raise SystemExit(f"Windows package incomplete: {name}")
print(f"PASS: complete release archives and {len(checksums)} SHA256 checksums verified.")
