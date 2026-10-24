"""Require fresh source-bound WPA2/WPA3/hidden WLAN and actual VHCI bond evidence."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

# Read the runner's literal pins without importing its QEMU/YAML dependencies.
PINS = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in ast.parse(Path(__file__).with_name("test-virtual-linux.py").read_text()).body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id in {"VERSION", "DIGESTS"}
}
MARKERS = [
    "RAMPI_RUST_WIFI_WPA3_SAE_OK",
    "RAMPI_RUST_WIFI_HIDDEN_SAE_OK",
    "RAMPI_WPA3_VISIBLE_HIDDEN_MODES_OK",
    "RAMPI_RUST_BLUEZ_VHCI_PAIR_TRUST_OK",
    "RAMPI_BLUEZ_VHCI_BOTH_BONDS_OK",
    "RAMPI_RUST_BLUEZ_VHCI_REMOVE_POWER_OK",
    "RAMPI_VIRTUAL_ACCEPTANCE_OK",
    "RAMPI_GUEST_EXIT=0",
]


def check_metadata(data, expected_binary=None):
    arch = data.get("architecture")
    if arch not in PINS["DIGESTS"]:
        raise ValueError("Unsupported radio test architecture")
    if (
        data.get("image_version") != PINS["VERSION"]
        or data.get("image_sha512") != PINS["DIGESTS"][arch]
    ):
        raise ValueError("Radio test did not use the pinned official system")
    for key in [
        "physical_devices",
        "prepared_development_cache",
        "resumed_development_guest",
        "graphical_login",
    ]:
        if data.get(key) is not False:
            raise ValueError("Radio test must use a fresh isolated guest: " + key)
    if data.get("memory_mib") != 1024 or data.get("cpus") != 4:
        raise ValueError("Radio test guest budget differs")
    if expected_binary is not None and data.get("native_binary_sha256") != expected_binary:
        raise ValueError("Radio test executable differs from the actual build")


def check(directory, expected_binary=None):
    metadata = json.loads((directory / "environment.json").read_text())
    check_metadata(metadata, expected_binary)
    binary = (directory / "source/rampi-network-acceptance").read_bytes()
    machine = 183 if metadata["architecture"] == "arm64" else 62
    if (
        len(binary) < 64
        or binary[:6] != b"\x7fELF\x02\x01"
        or int.from_bytes(binary[18:20], "little") != machine
    ):
        raise ValueError("Radio proof does not contain the matching native ELF")
    if hashlib.sha256(binary).hexdigest() != metadata.get("native_binary_sha256"):
        raise ValueError("Radio test executable checksum mismatch")
    log = (directory / "serial.log").read_text(errors="replace")
    for marker in MARKERS:
        if marker not in log:
            raise ValueError("Missing actual virtual radio result: " + marker)
    if log.count("RAMPI_RUST_WIFI_OTHER_USER_OK") < 3 or log.count("RAMPI_RUST_WIFI_LIVE_OK") < 3:
        raise ValueError("Not all WLAN modes passed private-profile and traffic checks")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary")
    args = parser.parse_args()
    check(args.directory, args.expected_binary)
    print("PASS: fresh WPA2/WPA3/hidden WLAN, private profiles and actual BlueZ VHCI bonds.")
