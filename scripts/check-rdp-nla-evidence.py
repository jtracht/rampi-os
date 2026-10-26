"""Reject omitted, failed or different-program native NLA acceptance."""

import argparse
import json
import re
from pathlib import Path


def check(directory, expected_binary=None):
    report = json.loads((directory / "nla-environment.json").read_text(encoding="utf-8"))
    digest = report.get("binary_sha256", "")
    if not re.fullmatch("[a-f0-9]{64}", digest) or expected_binary and digest != expected_binary:
        raise ValueError("NLA acceptance used another or unidentified program")
    if (
        report.get("windows_host") is not False
        or report.get("private_network") is not True
        or report.get("published_ports") is not False
        or report.get("server") != "FreeRDP/WinPR"
        or report.get("security") != "nla-only"
        or report.get("domain") != "RAMPI"
        or report.get("bad_certificate_rejected") is not True
        or report.get("bad_credentials_rejected") is not True
        or report.get("reconnected") is not True
        or report.get("keyboard_receipts") != 2
    ):
        raise ValueError("Missing real private NLA authentication/rejection/reconnect")
    log = (directory / "nla-client.log").read_text(encoding="utf-8")
    for marker in (
        "RAMPI_RUST_RDP_BAD_CERTIFICATE_OK",
        "RAMPI_RUST_RDP_NLA_BAD_ACCOUNT_REJECT_OK",
        "RAMPI_RUST_RDP_NLA_DOMAIN_RECONNECT_OK",
    ):
        if marker not in log:
            raise ValueError("Missing actual native NLA result: " + marker)
    receipts = (directory / "nla-keyboard-receipts.txt").read_text(encoding="utf-8").splitlines()
    if not {"rampinla0", "rampinla1"}.issubset(receipts):
        raise ValueError("NLA desktop did not receive keyboard input after both logins")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary")
    options = parser.parse_args()
    check(options.directory, options.expected_binary)
    print("PASS: actual native NLA-only authentication, rejection, frames and input/reconnect.")
