"""Package source and host adapter without credentials or development environments."""

from __future__ import annotations

import hashlib
import re
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = re.search(
    r'__version__ = "([^"]+)"', (ROOT / "client/rampi/__init__.py").read_text()
).group(1)
output = ROOT / "artifacts/release"
output.mkdir(parents=True, exist_ok=True)
include = [
    "client",
    "host",
    "installer",
    "system",
    "docs",
    "examples",
    "assets",
    "image",
    "packaging",
    "scripts",
    "tests",
    "setup.sh",
    "setup.ps1",
    "pyproject.toml",
    "LICENSE",
    "NOTICE",
    "README.md",
    "CHANGELOG.md",
    "requirements-runtime.txt",
]
files = []
for name in include:
    path = ROOT / name
    files.extend(
        [path]
        if path.is_file()
        else [
            p
            for p in path.rglob("*")
            if p.is_file() and not any(part in {"__pycache__", ".pytest_cache"} for part in p.parts)
        ]
    )
with tarfile.open(output / f"rampi-source-{version}.tar.gz", "w:gz") as archive:
    for path in sorted(files):
        info = archive.gettarinfo(
            str(path), arcname=f"rampi-os/{path.relative_to(ROOT).as_posix()}"
        )
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = "root"
        info.mode = (
            0o755 if path.suffix == ".sh" or path.name in {"rampi", "rampi-session"} else 0o644
        )
        with path.open("rb") as stream:
            archive.addfile(info, stream)
with zipfile.ZipFile(
    output / f"rampi-windows-host-{version}.zip", "w", zipfile.ZIP_DEFLATED
) as archive:
    for path in sorted(files):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in {"host", "installer"} and ("windows" in rel.parts):
            archive.write(path, rel.as_posix())
    for name in ["setup.ps1", "LICENSE", "NOTICE"]:
        archive.write(ROOT / name, name)
for name in ["setup.sh", "setup.ps1", "LICENSE", "NOTICE"]:
    if name.startswith("setup."):
        bootstrap = (ROOT / name).read_text(encoding="utf-8")
        bootstrap = bootstrap.replace("'0.1.0.dev0'", f"'{version}'")
        (output / name).write_text(bootstrap, encoding="utf-8", newline="\n")
    else:
        shutil.copyfile(ROOT / name, output / name)
checksums = []
for path in sorted(output.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS":
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
(output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
print(f"Packaged Rampi {version} in {output}")
