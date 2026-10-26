"""Check private real-kernel Tailscale evidence; never claim public OAuth."""

import argparse
import json
import re
from pathlib import Path


def check(directory, expected_binary=None):
    report = json.loads((directory / "environment.json").read_text(encoding="utf-8"))
    digest = report.get("native_binary_sha256", "")
    if not re.fullmatch("[a-f0-9]{64}", digest) or expected_binary and digest != expected_binary:
        raise ValueError("Tailscale test used another or unidentified native program")
    for key in (
        "private_dns_aliases", "private_network", "actual_kernel_tun",
        "bidirectional_icmp", "down_blocks_traffic", "reconnect_restores_traffic",
        "other_user_change_denied", "unrelated_routes_preserved",
        "existing_preferences_preserved",
        "embedded_operator_pam",
    ):
        if report.get(key) is not True:
            raise ValueError("Missing actual Tailscale boundary: " + key)
    for key in ("public_provider_oauth_tested", "published_ports", "physical_devices",
                "userspace_fake_tunnel"):
        if report.get(key) is not False:
            raise ValueError("Private tunnel evidence overstates its scope: " + key)
    if report.get("enrolled_nodes") != 2 or not report.get("control_server_version"):
        raise ValueError("Missing actual coordinator version or two enrolled nodes")
    if not isinstance(report.get("client_version"), dict):
        raise ValueError("Missing actual official client version")
    log = (directory / "native-tailscale.log").read_text(encoding="utf-8")
    for marker in (
        "RAMPI_RUST_TAILSCALE_OPERATOR_BAD_PASSWORD_REJECTED",
        "RAMPI_RUST_TAILSCALE_OPERATOR_EMBEDDED_PAM_OK",
    ):
        if log.splitlines().count(marker) != 1:
            raise ValueError("Missing actual embedded sudo/PAM receipt: " + marker)
    for action, count in (("action-login", 2), ("action-denied-down", 1),
                          ("action-down", 1), ("action-up", 1)):
        if log.splitlines().count("RAMPI_RUST_TAILSCALE_ACTION_OK " + action) != count:
            raise ValueError("Missing native Tailscale action receipt: " + action)
    for filename in ("icmp-0-1.log", "icmp-1-0.log", "icmp-reconnected.log"):
        traffic = (directory / filename).read_text(encoding="utf-8")
        if not re.search(r"2 packets transmitted, 2 received, 0% packet loss", traffic):
            raise ValueError("Both actual kernel peers must receive traffic")
    blocked = (directory / "icmp-disconnected.log").read_text(encoding="utf-8")
    if not re.search(r"1 packets transmitted, 0 received", blocked):
        raise ValueError("Disconnected peer still received data or result is missing")
    if "Access denied" not in (directory / "other-user-denied.log").read_text(encoding="utf-8"):
        raise ValueError("Official daemon did not explicitly deny the unrelated UID")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary")
    options = parser.parse_args()
    check(options.directory, options.expected_binary)
    print("PASS: private actual Tailscale tunnel, enrollment, rights, disconnect/reconnect.")
