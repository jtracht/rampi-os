"""Reject missing work-budget and executable provenance in measured UI evidence."""

import json
import runpy
from pathlib import Path

import pytest

check = runpy.run_path(str(Path(__file__).resolve().parents[1]
                          / "scripts/check-animation-evidence.py"))["check"]


def evidence():
    return {"schema": 1, "native_elf_sha256": "a" * 64, "single_window": True,
            "complete_product_acceptance": False, "idle_ticks": 0, "reduced_ticks": 0,
            "active_paints": 18, "active_window_ms": 600,
            "scope": "headless GTK; not Raspberry Pi timing"}


def write(tmp_path, proof):
    (tmp_path / "animation-scheduling.json").write_text(json.dumps(proof))


def test_accept_budget_receipt_without_claiming_hardware_timing(tmp_path):
    write(tmp_path, evidence())
    assert check(tmp_path, "a" * 64)["idle_ticks"] == 0


@pytest.mark.parametrize("key,value", [
    ("idle_ticks", 1), ("idle_ticks", False), ("reduced_ticks", 1),
    ("active_paints", 0), ("active_paints", 40),
    ("active_paints", True), ("active_paints", float("nan")),
    ("native_elf_sha256", "b" * 64), ("single_window", False),
    ("complete_product_acceptance", True), ("scope", "Hardware test"),
    ("schema", True), ("scope", None), ("active_window_ms", 0),
    ("active_window_ms", True), ("active_window_ms", float("nan")),
])
def test_reject_stale_or_invalid_measurements(tmp_path, key, value):
    proof = evidence()
    proof[key] = value
    write(tmp_path, proof)
    with pytest.raises(ValueError):
        check(tmp_path, "a" * 64)


def test_missing_measurement_is_not_accepted(tmp_path):
    with pytest.raises(FileNotFoundError):
        check(tmp_path, "a" * 64)
