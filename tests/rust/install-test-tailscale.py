"""Install a pinned official CLI/daemon only into the disposable test image."""

import hashlib
import io
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

VERSION = "1.104.2"
AMD64_SHA256 = (
    "512f613ed7d04fc7282f7dc5bd76aa105aae28168fbb9357eb749ebcbc29f0ae"  # pragma: allowlist secret
)
ARM64_SHA256 = (
    "5776aaa901b5ef1916e66be5bb54b9f481cd399c9c28db123a8cab620efa237b"  # pragma: allowlist secret
)
PACKAGES = {
    "x86_64": ("amd64", AMD64_SHA256),
    "aarch64": ("arm64", ARM64_SHA256),
}
architecture, checksum = PACKAGES[platform.machine()]
if shutil.which("tailscale") or shutil.which("tailscaled"):
    existing = subprocess.check_output(["tailscale", "version"], text=True).splitlines()[0]
    if existing != VERSION:
        raise SystemExit(
            "Existing incompatible Tailscale test installation; refusing to replace it"
        )
else:
    name = f"tailscale_{VERSION}_{architecture}"
    with urllib.request.urlopen(
        f"https://pkgs.tailscale.com/stable/{name}.tgz", timeout=60
    ) as response:
        data = response.read(100 * 1024 * 1024 + 1)
    if len(data) > 100 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != checksum:
        raise SystemExit("Official Tailscale test archive checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for binary in ("tailscale", "tailscaled"):
            member = archive.extractfile(f"{name}/{binary}")
            if member is None:
                raise SystemExit("Official archive is missing a required binary")
            target = Path("/usr/local/bin") / binary
            target.write_bytes(member.read())
            target.chmod(0o755)
print(f"Pinned official Tailscale {VERSION} installed for {architecture} software tests")
