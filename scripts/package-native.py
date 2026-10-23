"""Package the real native ARM64 executable and original dependency licenses."""

import argparse
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--binary", required=True, type=Path)
parser.add_argument("--licenses", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
version = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))["workspace"]["package"][
    "version"
]
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
for options in [["diff", "--quiet"], ["diff", "--cached", "--quiet"]]:
    if subprocess.run(["git", *options], cwd=root, check=False).returncode:
        raise SystemExit("Commit source changes before creating a native package")
binary = args.binary.read_bytes()
if binary[:6] != b"\x7fELF\x02\x01" or int.from_bytes(binary[18:20], "little") != 183:
    raise SystemExit("Native package requires a little-endian ARM64 ELF executable")
reported = subprocess.check_output([str(args.binary.resolve()), "--version"], text=True).strip()
if reported != f"Rampi {version} (Rust / Wayland)":
    raise SystemExit("Native executable and source versions differ")
for name in ["packages.json", "Rust-standard-library-COPYRIGHT.html"]:
    if not (args.licenses / name).is_file():
        raise SystemExit("Original Rust dependency licenses are missing: " + name)
args.output.mkdir(parents=True, exist_ok=True)
target = args.output / f"rampi-linux-arm64-{version}.tar.xz"
with tempfile.TemporaryDirectory(prefix="rampi-native-package-") as temporary:
    stage = Path(temporary) / "bin"
    stage.mkdir()
    shutil.copyfile(args.binary, stage / "rampi-native")
    (stage / "rampi-native").chmod(0o755)
    shutil.copytree(args.licenses, stage / "rust-licenses")
    (stage / "binary-sha256.txt").write_text(hashlib.sha256(binary).hexdigest() + "\n")
    (stage / "source-revision.txt").write_text(revision + "\n")
    for name in ["LICENSE", "NOTICE"]:
        shutil.copyfile(root / name, stage / name)
    with tarfile.open(target, "w:xz") as archive:
        for path in [stage, *sorted(stage.rglob("*"))]:
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise SystemExit("Native package contains a non-regular member")
            item = archive.gettarinfo(str(path), arcname=path.relative_to(stage.parent).as_posix())
            item.uid = item.gid = 0
            item.uname = item.gname = "root"
            item.mode = 0o755 if path.is_dir() or path.name == "rampi-native" else 0o644
            if path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(item, stream)
            else:
                archive.addfile(item)
print(f"Packaged real ARM64 executable, source {revision}: {target}")
