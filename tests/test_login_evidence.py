"""Release evidence must reject resumed VMs, wrong identities and stale binaries."""

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "login_evidence", Path(__file__).resolve().parents[1] / "scripts/check-login-evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
DIGEST = "a" * 64


@pytest.fixture
def evidence(tmp_path):
    environment = {
        "architecture": "arm64",
        "memory_mib": 1024,
        "cpus": 4,
        "tcg_thread": "multi",
        "physical_devices": False,
        "prepared_development_cache": False,
        "resumed_development_guest": False,
        "graphical_login": True,
        "native_binary_sha256": DIGEST,
    }
    (tmp_path / "environment.json").write_text(json.dumps(environment))
    (tmp_path / "serial.log").write_text(
        "\n".join(
            [
                "RAMPI_GRAPHICAL_LOGIN_NO_UNAUTH_UI_OK",
                "RAMPI_GRAPHICAL_LOGIN_REJECT_OK",
                "RAMPI_GRAPHICAL_LOGIN_TWO_USERS_OK",
                "RAMPI_GRAPHICAL_LOGIN_SSH_AGENT_OK",
                "RAMPI_GRAPHICAL_LOGIN_BRANDING_OK",
                "RAMPI_GRAPHICAL_LOGIN_OK",
                "RAMPI_GUEST_EXIT=0",
            ]
        )
    )
    capture = tmp_path / "captures"
    capture.mkdir()
    proof = [
        {
            "uid": uid,
            "session_uid": uid,
            "config_uid": uid,
            "ssh_agent_private": True,
            "config_mode": "0o700",
            "native_process": True,
            "binary_sha256": DIGEST,
        }
        for uid in [1001, 1002]
    ]
    (capture / "login-proof.json").write_text(json.dumps(proof))
    for name in ["greeter", "rampi-login", "rampi-other"]:
        Image.new("RGB", (1280, 720), (80, 100, 120)).save(capture / (name + ".png"))
    # Synthetic checker fixture, deliberately not a runtime screenshot.
    greeter = Image.open(capture / "greeter.png")
    greeter.paste((200, 20, 70), (80, 80, 150, 150))
    greeter.paste((20, 150, 60), (80, 45, 130, 65))
    greeter.save(capture / "greeter.png")
    return tmp_path


def test_reject_black_compositor_with_only_cursor(evidence):
    picture = evidence / "captures/rampi-login.png"
    image = Image.new("RGB", (1280, 720))
    image.paste((255, 255, 255), (90, 90, 100, 100))
    image.save(picture)
    with pytest.raises(ValueError, match="not been painted"):
        MODULE.check(evidence)


def test_fresh_two_account_evidence(evidence):
    assert MODULE.check(evidence, DIGEST)["architecture"] == "arm64"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("prepared_development_cache", True),
        ("resumed_development_guest", True),
        ("physical_devices", True),
        ("graphical_login", False),
        ("memory_mib", 2048),
        ("tcg_thread", "single"),
    ],
)
def test_reject_wrong_test_scope(evidence, key, value):
    path = evidence / "environment.json"
    data = json.loads(path.read_text())
    data[key] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        MODULE.check(evidence)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("session_uid", 0),
        ("config_uid", 0),
        ("config_mode", "0o755"),
        ("binary_sha256", "b" * 64),
        ("native_process", False),
        ("ssh_agent_private", False),
        ("uid", 1001),
    ],
)
def test_reject_insecure_or_stale_session(evidence, key, value):
    path = evidence / "captures/login-proof.json"
    data = json.loads(path.read_text())
    data[1][key] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        MODULE.check(evidence)


def test_reject_missing_pam_rejection(evidence):
    path = evidence / "serial.log"
    path.write_text(path.read_text().replace("RAMPI_GRAPHICAL_LOGIN_REJECT_OK", ""))
    with pytest.raises(ValueError):
        MODULE.check(evidence)


def test_reject_later_guest_failure(evidence):
    path = evidence / "serial.log"
    path.write_text(path.read_text() + "\nRAMPI_GUEST_EXIT=1")
    with pytest.raises(ValueError):
        MODULE.check(evidence)


def test_reject_binary_not_from_producer(evidence):
    with pytest.raises(ValueError):
        MODULE.check(evidence, "b" * 64)


def test_reject_unbranded_login(evidence):
    Image.new("RGB", (1280, 720), (80, 100, 120)).save(evidence / "captures/greeter.png")
    with pytest.raises(ValueError, match="logo missing"):
        MODULE.check(evidence)
