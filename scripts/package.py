"""Package source and host adapter without credentials or development environments."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))["workspace"]["package"][
    "version"
]
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

output = ROOT / "artifacts/release"
output.mkdir(parents=True, exist_ok=True)
for options in [["diff", "--quiet"], ["diff", "--cached", "--quiet"]]:
    if subprocess.run(["git", *options], cwd=ROOT, check=False).returncode:
        raise SystemExit("Commit tracked changes before packaging an immutable source revision.")
windows_files = subprocess.check_output(
    ["git", "ls-files", "-z", "--", "installer/windows"], cwd=ROOT
).decode("utf-8").split("\0")
subprocess.run(
    [
        "git",
        "archive",
        "--format=tar.gz",
        "--prefix=rampi-os/",
        "--add-virtual-file=rampi-os/source-revision.txt:" + revision,
        "--output=" + str(output / f"rampi-source-{version}.tar.gz"),
        "HEAD",
    ],
    cwd=ROOT,
    check=True,
)
with zipfile.ZipFile(
    output / f"rampi-windows-host-{version}.zip", "w", zipfile.ZIP_DEFLATED
) as archive:
    for name in sorted(filter(None, windows_files)):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit("Windows package requires regular tracked files: " + name)
        archive.write(path, name)
    for name in ["setup.ps1", "LICENSE", "NOTICE"]:
        archive.write(ROOT / name, name)
    archive.write(ROOT / "docs/INSTALL-WINDOWS11.md", "README.md")
    archive.write(ROOT / "docs/STREAMING.md", "STREAMING.md")
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
