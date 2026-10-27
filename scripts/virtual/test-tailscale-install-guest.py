"""Actual signed manual-install helper and vendor systemd service in a fresh private VM."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

SOURCE = Path("/opt/rampi-source")
CAPTURES = Path("/opt/rampi-captures")


def command(*args, check=True):
    return subprocess.run(args, capture_output=True, check=check, timeout=30)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (os.geteuid() or not Path("/etc/rampi-acceptance-vm").is_file()
            or Path("/proc/1/comm").read_text().strip() != "systemd"):
        raise RuntimeError("Only in the designated full-system disposable guest")
    command("systemd-detect-virt", "--vm", "--quiet")
    helper = Path("/usr/local/libexec/rampi-tailscale-install")
    key = Path("/usr/share/rampi/tailscale-archive-keyring.gpg")
    if any(path.exists() or path.is_symlink() for path in (
        helper, key, Path("/usr/bin/tailscale"), Path("/usr/local/bin/tailscale"),
    )):
        raise RuntimeError("The fresh installation component must not reuse a prior installation")
    os.umask(0o077)
    for target, source, mode in (
        (helper, SOURCE / "system/rampi-tailscale-install", 0o755),
        (key, SOURCE / "installer/raspberrypi/tailscale-archive-keyring.gpg", 0o644),
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.parent.chmod(0o755)
        shutil.copyfile(source, target)
        target.chmod(mode)
    log = CAPTURES / "tailscale-install.log"
    started = False
    try:
        with log.open("wb") as output:
            subprocess.run([str(helper), "--install"], stdout=output,
                           stderr=subprocess.STDOUT, check=True, timeout=420)
        started = True
        command("systemctl", "is-enabled", "--quiet", "tailscaled.service")
        command("systemctl", "is-active", "--quiet", "tailscaled.service")
        fragment = Path(command(
            "systemctl", "show", "-p", "FragmentPath", "--value", "tailscaled.service",
        ).stdout.decode().strip()).resolve()
        package_files = command("dpkg-query", "-L", "tailscale").stdout.decode().splitlines()
        if fragment not in {Path(name).resolve() for name in package_files if name.endswith(
            "/tailscaled.service",
        )}:
            raise RuntimeError("The running unit is not owned by the installed vendor package")
        pid = int(command("systemctl", "show", "-p", "MainPID", "--value",
                          "tailscaled.service").stdout)
        if (pid <= 1 or Path(f"/proc/{pid}/comm").read_text().strip() != "tailscaled"
                or Path(f"/proc/{pid}/exe").resolve() != Path("/usr/sbin/tailscaled").resolve()):
            raise RuntimeError("The actual existing vendor daemon is not running")
        version = command("tailscale", "version").stdout.decode().splitlines()[0]
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
            raise RuntimeError("Unexpected installed official CLI version")
        deadline = time.monotonic() + 60
        while True:
            result = command("tailscale", "status", "--json", check=False)
            try:
                state = json.loads(result.stdout).get("BackendState")
            except ValueError:
                state = None
            if state == "NeedsLogin":
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("The real CLI did not reach its unauthenticated daemon")
            time.sleep(0.5)
        retained = [helper, key, Path("/usr/bin/tailscale"),
                    Path("/etc/apt/sources.list.d/rampi-tailscale.list"),
                    Path("/usr/share/keyrings/rampi-tailscale.gpg"),
                    Path("/etc/apt/apt.conf.d/52rampi-tailscale-manual")]
        before = [(sha(path), path.stat().st_ino, path.stat().st_mtime_ns) for path in retained]
        command(str(helper), "--install")
        after = [(sha(path), path.stat().st_ino, path.stat().st_mtime_ns) for path in retained]
        if before != after or int(command(
            "systemctl", "show", "-p", "MainPID", "--value", "tailscaled.service",
        ).stdout) != pid:
            raise RuntimeError("Repeated manual installation changed the existing service/files")
        if sha(helper) != sha(SOURCE / "system/rampi-tailscale-install"):
            raise RuntimeError("Another installer helper was executed")
        proof = {
            "signed_apt_install": True, "existing_vendor_systemd_unit": True,
            "enabled": True, "active_vendor_daemon": True, "cli_reached_daemon": True,
            "backend_state": state, "version": version,
            "repeated_install_preserved_files_and_pid": True,
            "helper_sha256": sha(helper), "binary_sha256": sha(Path("/usr/bin/tailscale")),
            "enrollment_performed": False, "tunnel_traffic_claimed": False,
            "physical_devices": False,
        }
        destination = CAPTURES / "tailscale-install-proof.json"
        destination.write_text(json.dumps(proof, indent=2) + "\n")
        destination.chmod(0o644)
        print("RAMPI_TAILSCALE_SYSTEMD_INSTALL_OK", flush=True)
    finally:
        if log.exists():
            log.chmod(0o644)
        if started:
            command("systemctl", "stop", "tailscaled.service", check=False)


if __name__ == "__main__":
    main()
