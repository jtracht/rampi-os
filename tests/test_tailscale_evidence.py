"""Reject incomplete tunnel receipts; fixture data is not a live VPN proof."""

import json
import runpy
from pathlib import Path

import pytest

CHECK = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check-tailscale-evidence.py"))[
    "check"
]


@pytest.fixture
def evidence(tmp_path):
    report = dict.fromkeys((
        "private_dns_aliases", "private_network", "actual_kernel_tun", "bidirectional_icmp",
        "down_blocks_traffic", "reconnect_restores_traffic", "other_user_change_denied",
        "unrelated_routes_preserved",
        "existing_preferences_preserved",
    ), True)
    report.update(dict.fromkeys(("public_provider_oauth_tested", "published_ports",
                               "physical_devices", "userspace_fake_tunnel"), False))
    report.update(native_binary_sha256="a" * 64, enrolled_nodes=2,
                  control_server_version="fixture", client_version={"Long": "fixture"})
    (tmp_path / "environment.json").write_text(json.dumps(report))
    actions = ["action-login", "action-login", "action-denied-down", "action-down", "action-up"]
    (tmp_path / "native-tailscale.log").write_text("".join(
        "RAMPI_RUST_TAILSCALE_ACTION_OK " + action + "\n" for action in actions
    ))
    for name in ("icmp-0-1.log", "icmp-1-0.log", "icmp-reconnected.log"):
        (tmp_path / name).write_text("2 packets transmitted, 2 received, 0% packet loss\n")
    (tmp_path / "icmp-disconnected.log").write_text("1 packets transmitted, 0 received\n")
    (tmp_path / "other-user-denied.log").write_text("Access denied: prefs write access denied\n")
    return tmp_path


@pytest.mark.parametrize("boundary", ["actual_kernel_tun", "reconnect_restores_traffic",
                                     "other_user_change_denied", "unrelated_routes_preserved"])
def test_missing_boundary_rejected(evidence, boundary):
    path = evidence / "environment.json"
    report = json.loads(path.read_text())
    report.pop(boundary)
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        CHECK(evidence)


def test_receipts_and_program_must_match(evidence):
    CHECK(evidence, "a" * 64)
    with pytest.raises(ValueError):
        CHECK(evidence, "b" * 64)
    (evidence / "icmp-1-0.log").write_text("2 packets transmitted, 0 received\n")
    with pytest.raises(ValueError):
        CHECK(evidence)


def test_public_oauth_claim_rejected(evidence):
    path = evidence / "environment.json"
    report = json.loads(path.read_text())
    report["public_provider_oauth_tested"] = True
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        CHECK(evidence)
