"""Pinned existing control server, only inside the disposable VPN test image."""

import hashlib
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

VERSION = "0.29.6"
PACKAGES = {
    "x86_64": (
        "amd64",
        # pragma: allowlist nextline secret
        "7477c374949eea6fb7cf3cbff14dbef49e4d118d9a33557d6764a77ece617e53",
    ),
    "aarch64": (
        "arm64",
        # pragma: allowlist nextline secret
        "7b3c792ebe10e1a81a0c8d9674aee8eb540e7dbb7ccb80a98b71024da4c72a48",
    ),
}
existing = shutil.which("headscale")
if existing:
    if VERSION not in subprocess.check_output([existing, "version"], text=True):
        raise SystemExit("An incompatible existing test server will not be replaced")
else:
    architecture, expected = PACKAGES[platform.machine()]
    url = f"https://github.com/juanfont/headscale/releases/download/v{VERSION}/headscale_{VERSION}_linux_{architecture}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(128 * 1024 * 1024 + 1)
    if len(data) > 128 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("Official Headscale asset checksum does not match")
    target = Path("/usr/local/bin/headscale")
    target.write_bytes(data)
    target.chmod(0o755)
    subprocess.run([str(target), "version"], check=True)
