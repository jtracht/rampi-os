"""Evidence guards; these synthetic inputs never count as an NLA server test."""

import json
import runpy
from pathlib import Path

import pytest

CHECK = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check-rdp-nla-evidence.py"))[
    "check"
]


@pytest.fixture
def evidence(tmp_path):
    report = {
        "windows_host": False,
        "private_network": True,
        "published_ports": False,
        "server": "FreeRDP/WinPR",
        "security": "nla-only",
        "domain": "RAMPI",
        "bad_certificate_rejected": True,
        "bad_credentials_rejected": True,
        "reconnected": True,
        "keyboard_receipts": 2,
        "binary_sha256": "a" * 64,
    }
    (tmp_path / "nla-environment.json").write_text(json.dumps(report))
    (tmp_path / "nla-keyboard-receipts.txt").write_text("rampinla0\nrampinla1\n")
    (tmp_path / "nla-client.log").write_text(
        "RAMPI_RUST_RDP_BAD_CERTIFICATE_OK\n"
        "RAMPI_RUST_RDP_NLA_BAD_ACCOUNT_REJECT_OK\n"
        "RAMPI_RUST_RDP_NLA_DOMAIN_RECONNECT_OK\n"
    )
    return tmp_path, report


def test_complete_guard_input(evidence):
    folder, report = evidence
    assert CHECK(folder, "a" * 64) == report


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("windows_host", True),
        ("private_network", False),
        ("published_ports", True),
        ("security", "tls"),
        ("bad_certificate_rejected", False),
        ("bad_credentials_rejected", False),
        ("reconnected", False),
        ("keyboard_receipts", 1),
        ("binary_sha256", "b" * 64),
    ],
)
def test_wrong_environment_or_other_program_fails(evidence, field, value):
    folder, report = evidence
    report[field] = value
    (folder / "nla-environment.json").write_text(json.dumps(report))
    with pytest.raises(ValueError):
        CHECK(folder, "a" * 64)


def test_tls_success_does_not_substitute_for_nla(evidence):
    folder, _ = evidence
    (folder / "nla-client.log").write_text("RAMPI_RUST_RDP_EMBEDDED_RECONNECT_OK\n")
    with pytest.raises(ValueError):
        CHECK(folder)


def test_no_server_receipt_after_reconnect_is_rejected(evidence):
    folder, _ = evidence
    (folder / "nla-keyboard-receipts.txt").write_text("rampinla0\n")
    with pytest.raises(ValueError):
        CHECK(folder)
