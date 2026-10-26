"""Verify the shipped archives and every checksum before publication."""

import argparse
import hashlib
import json
import re
import runpy
import tarfile
import tomllib
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--image", action="store_true")
args = parser.parse_args()
directory = args.directory
required = {"setup.sh", "setup.ps1", "LICENSE", "NOTICE"}
version = tomllib.loads(
    (Path(__file__).resolve().parents[1] / "Cargo.toml").read_text(encoding="utf-8")
)["workspace"]["package"]["version"]
source = f"rampi-source-{version}.tar.gz"
host = f"rampi-windows-host-{version}.zip"
required.update([source, host])
if args.image:
    images = list(directory.glob("*.img.xz"))
    if len(images) != 1:
        raise SystemExit("Exactly one flashable image required")
    required.update(
        [
            images[0].name,
            "package-manifest.tsv",
            "dependency-licenses.tar.xz",
            "debian-source-archives.json",
            "rust-dependency-sources.tar.xz",
            "qemu-boot.log",
            "qemu-environment.txt",
            "partitions.json",
            "pi-gen-revision.txt",
            "readiness.json",
            "release-ci.json",
            f"rampi-linux-arm64-{version}.tar.xz",
        ]
    )
    transport = runpy.run_path(str(Path(__file__).with_name("release-assets.py")))
    required.update(transport["source_assets"](directory))
    if (directory / transport["INDEX"]).exists():
        required.update({"restore-dependency-sources.py", "DEPENDENCY-SOURCES.txt"})
    transport["check_limits"](directory)
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
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/rust.yml",
        "scripts/check-release-ci.py",
        "scripts/release-assets.py",
        "LICENSE",
        "client/rampi/qml/Main.qml",
        "client/rampi/icons/LICENSE",
        "image/build.sh",
        "installer/raspberrypi/setup.sh",
        "installer/raspberrypi/keyring-profile.sh",
        "installer/raspberrypi/keyring-profile-user.sh",
        "system/rampi-keyring-ordering.conf",
        "docs/INSTALL-RASPBERRYPI.md",
        "setup.sh",
        "source-revision.txt",
        "Cargo.toml",
        "Cargo.lock",
        "native/ui/src/linux.rs",
        "native/core/src/config.rs",
        "system/labwc/rc.xml",
        "docs/RUST-MIGRATION.md",
    ]:
        if "rampi-os/" + name not in entries:
            raise SystemExit(f"Source archive incomplete: {name}")
if args.image or (directory / f"rampi-linux-arm64-{version}.tar.xz").is_file():
    with tarfile.open(directory / f"rampi-linux-arm64-{version}.tar.xz") as native:
        for item in native.getmembers():
            path = Path(item.name)
            if path.is_absolute() or ".." in path.parts or not (item.isfile() or item.isdir()):
                raise SystemExit("Unsafe native bundle member")

        def read_native(name):
            item = native.getmember("bin/" + name)
            if not item.isfile():
                raise SystemExit("Native bundle metadata must be regular files")
            return native.extractfile(item).read()

        binary = read_native("rampi-native")
        if binary[:5] != b"\x7fELF\x02" or int.from_bytes(binary[18:20], "little") != 183:
            raise SystemExit("Native bundle is not ARM64 ELF")
        if hashlib.sha256(binary).hexdigest() != read_native("binary-sha256.txt").decode().strip():
            raise SystemExit("Native bundle binary checksum mismatch")
        with tarfile.open(directory / source) as sources:
            revision = sources.extractfile("rampi-os/source-revision.txt").read().decode().strip()
            source_lock = sources.extractfile("rampi-os/Cargo.lock").read()
        if (
            not re.fullmatch(r"[a-f0-9]{40}", revision)
            or revision != read_native("source-revision.txt").decode().strip()
        ):
            raise SystemExit("Native bundle and source revisions differ")
        read_native("rust-licenses/packages.json")
        read_native("rust-licenses/Rust-standard-library-COPYRIGHT.html")
if args.image:
    runpy.run_path(str(Path(__file__).with_name("check-source-archives.py")))["check"](
        directory, revision, source_lock
    )
    verifier = runpy.run_path(str(Path(__file__).with_name("check-release-ci.py")))
    try:
        verifier["validate_proof"](
            json.loads((directory / "release-ci.json").read_text(encoding="utf-8")),
            revision,
            tomllib.loads(
                (Path(__file__).resolve().parents[1] / "Cargo.toml").read_text(encoding="utf-8")
            )["workspace"]["package"]["repository"].removeprefix("https://github.com/"),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Release CI proof invalid: {error}") from error
with zipfile.ZipFile(directory / host) as archive:
    for name in [
        "setup.ps1",
        "installer/windows/setup.ps1",
        "STREAMING.md",
    ]:
        if name not in archive.namelist():
            raise SystemExit(f"Windows package incomplete: {name}")
print(f"PASS: complete release archives and {len(checksums)} SHA256 checksums verified.")
