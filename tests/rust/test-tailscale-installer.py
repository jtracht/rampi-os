"""Real filesystem preservation and privilege boundaries in a disposable fixture."""
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

if (
    os.geteuid()
    or os.environ.get("RAMPI_TEST_CONTAINER") != "1"
    or not Path("/.dockerenv").exists()
):
    raise SystemExit("Disposable root container required")

HELPER = "/src/system/rampi-tailscale-install"
CLI = Path("/usr/local/bin/tailscale")
REPO = Path("/etc/apt/sources.list.d/rampi-tailscale.list")
KEY = Path("/usr/share/keyrings/rampi-tailscale.gpg")
UPDATES = Path("/etc/apt/apt.conf.d/52rampi-tailscale-manual")


def snapshot():
    return {
        str(path): ("link", os.readlink(path)) if path.is_symlink()
        else ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        for path in Path("/etc/apt").rglob("*") if path.is_file() or path.is_symlink()
    }


def invoke(*prefix):
    return subprocess.run([*prefix, "bash", HELPER, "--install"], capture_output=True, timeout=20)


assert CLI.is_file() and not REPO.exists() and not KEY.exists() and not UPDATES.exists()
original = hashlib.sha256(CLI.read_bytes()).hexdigest()
before = snapshot()
assert invoke("runuser", "-u", "rampi", "--").returncode == 2
assert invoke().returncode == 0
assert snapshot() == before and hashlib.sha256(CLI.read_bytes()).hexdigest() == original

with tempfile.TemporaryDirectory(prefix="rampi-install-preservation-") as temporary:
    root = Path(temporary)
    CLI.rename(root / "original-cli")
    try:
        packaged = Path("/usr/share/rampi/tailscale-archive-keyring.gpg")
        packaged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile("/src/installer/raspberrypi/tailscale-archive-keyring.gpg", packaged)
        KEY.parent.mkdir(parents=True, exist_ok=True)
        for destination in (REPO, KEY):
            protected = root / "administrator-file"
            protected.write_text("existing administrator configuration\n")
            destination.symlink_to(protected)
            baseline = snapshot()
            assert invoke().returncode != 0
            assert destination.is_symlink() and destination.resolve() == protected
            assert protected.read_text() == "existing administrator configuration\n"
            assert snapshot() == baseline
            assert not UPDATES.exists()
            destination.unlink()
        UPDATES.write_text("// Existing administrator policy\n")
        baseline = snapshot()
        assert invoke().returncode != 0
        assert snapshot() == baseline and not REPO.exists() and not KEY.exists()
        UPDATES.unlink()
    finally:
        (root / "original-cli").rename(CLI)
assert hashlib.sha256(CLI.read_bytes()).hexdigest() == original
print("RAMPI_TAILSCALE_INSTALLER_PRESERVATION_OK")
print(
    "PASS: unprivileged refusal, existing official CLI reuse, administrator files and symlinks "
    "retained; no installation or tunnel claimed."
)
