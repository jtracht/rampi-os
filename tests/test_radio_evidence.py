"""Synthetic guard tests; these are not radio execution evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "radio_evidence", Path(__file__).resolve().parents[1] / "scripts/check-radio-evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def evidence(tmp_path):
    raw = bytearray(64)
    raw[:6] = b"\x7fELF\x02\x01"
    raw[18:20] = (62).to_bytes(2, "little")
    (tmp_path / "source").mkdir()
    (tmp_path / "source/rampi-network-acceptance").write_bytes(raw)
    data = dict(
        architecture="amd64",
        image_version=MODULE.PINS["VERSION"],
        image_sha512=MODULE.PINS["DIGESTS"]["amd64"],
        physical_devices=False,
        prepared_development_cache=False,
        resumed_development_guest=False,
        graphical_login=False,
        memory_mib=1024,
        cpus=4,
        native_binary_sha256=hashlib.sha256(raw).hexdigest(),
    )
    (tmp_path / "environment.json").write_text(json.dumps(data))
    log = "\n".join(
        MODULE.MARKERS + ["RAMPI_RUST_WIFI_OTHER_USER_OK", "RAMPI_RUST_WIFI_LIVE_OK"] * 3
    )
    (tmp_path / "serial.log").write_text(log)
    return data, log


def test_accept_complete_fresh_bound_results(tmp_path):
    data, _ = evidence(tmp_path)
    MODULE.check(tmp_path, data["native_binary_sha256"])


@pytest.mark.parametrize(
    "key,value",
    [
        ("architecture", "other"),
        ("image_version", "latest"),
        ("image_sha512", "bad"),
        ("physical_devices", True),
        ("prepared_development_cache", True),
        ("resumed_development_guest", True),
        ("graphical_login", True),
        ("memory_mib", 2048),
        ("cpus", 8),
    ],
)
def test_reject_different_or_reused_environment(tmp_path, key, value):
    data, _ = evidence(tmp_path)
    data[key] = value
    (tmp_path / "environment.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        MODULE.check(tmp_path)


@pytest.mark.parametrize("marker", MODULE.MARKERS)
def test_reject_omitted_execution_stage(tmp_path, marker):
    _, log = evidence(tmp_path)
    (tmp_path / "serial.log").write_text(log.replace(marker, ""))
    with pytest.raises(ValueError, match="Missing actual"):
        MODULE.check(tmp_path)


def test_reject_tampered_or_different_program(tmp_path):
    data, _ = evidence(tmp_path)
    with pytest.raises(ValueError, match="actual build"):
        MODULE.check(tmp_path, "a" * 64)
    (tmp_path / "source/rampi-network-acceptance").write_bytes(b"changed")
    with pytest.raises(ValueError):
        MODULE.check(tmp_path, data["native_binary_sha256"])


def test_reject_missing_modes_for_other_user(tmp_path):
    _, log = evidence(tmp_path)
    (tmp_path / "serial.log").write_text(log.replace("RAMPI_RUST_WIFI_OTHER_USER_OK", "", 1))
    with pytest.raises(ValueError, match="Not all WLAN modes"):
        MODULE.check(tmp_path)
