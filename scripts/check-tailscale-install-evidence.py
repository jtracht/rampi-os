"""Require the fresh VM's real signed APT installation and existing vendor service."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def check(directory):
    environment = json.loads((directory / "environment.json").read_text())
    for key, value in {
        "physical_devices": False, "prepared_development_cache": False,
        "resumed_development_guest": False, "graphical_login": True,
        "memory_mib": 1024, "cpus": 4,
    }.items():
        if type(environment.get(key)) is not type(value) or environment[key] != value:
            raise ValueError("Tailscale installation requires a fresh full-system guest: " + key)
    if environment.get("architecture") not in {"amd64", "arm64"}:
        raise ValueError("Unsupported Tailscale installation architecture")
    proof = json.loads((directory / "captures/tailscale-install-proof.json").read_text())
    for key in (
        "signed_apt_install", "existing_vendor_systemd_unit", "enabled",
        "active_vendor_daemon", "cli_reached_daemon", "repeated_install_preserved_files_and_pid",
    ):
        if proof.get(key) is not True:
            raise ValueError("Missing actual Tailscale installation evidence: " + key)
    for key in ("enrollment_performed", "tunnel_traffic_claimed", "physical_devices"):
        if proof.get(key) is not False:
            raise ValueError("Installation component cannot claim enrollment, traffic or hardware")
    source = Path(__file__).parents[1] / "system/rampi-tailscale-install"
    if (proof.get("backend_state") != "NeedsLogin"
            or proof.get("helper_sha256") != hashlib.sha256(source.read_bytes()).hexdigest()
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", proof.get("version", ""))
            or not re.fullmatch(r"[a-f0-9]{64}", proof.get("binary_sha256", ""))):
        raise ValueError("Tailscale installer source, actual CLI or vendor daemon differs")
    log = (directory / "serial.log").read_text(encoding="utf-8", errors="replace")
    if not all(marker in log for marker in (
        "RAMPI_TAILSCALE_SYSTEMD_INSTALL_OK", "RAMPI_GUEST_EXIT=0",
    )):
        raise ValueError("The actual full-system installation did not complete")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
    print("PASS: actual signed Tailscale installation, vendor systemd service and retained files.")
