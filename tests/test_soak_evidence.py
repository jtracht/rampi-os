"""Reject short, incomplete, unbounded or unconfirmed mixed-workload reports."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "soak_evidence", Path(__file__).resolve().parents[1] / "scripts/check-soak-evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def evidence(tmp_path):
    tokens = [f"rampisoak{cycle}" for cycle in range(0, 150, 15)]
    report = dict(
        duration_seconds=600.5,
        cycles=150,
        module_switches=1050,
        switch_p95_paint_ms=25,
        cgroup_cpu_percent_of_one_core=34,
        binary_sha256="a" * 64,
        live_ptys=3,
        webkit_javascript_roundtrips=150,
        distinct_remote_pixel_hashes=145,
        memory_limit_bytes=1024**3,
        swap_limit_bytes=0,
        cgroup_peak_memory_bytes=400 * 1024**2,
        warm_memory_bytes=350 * 1024**2,
        final_memory_bytes=360 * 1024**2,
        remote_input_tokens=tokens,
        samples=[
            dict(elapsed_seconds=(i + 1) * 4, cgroup_memory_bytes=350 * 1024**2) for i in range(150)
        ],
    )
    (tmp_path / "mixed-soak.json").write_text(json.dumps(report))
    (tmp_path / "acceptance.log").write_text(
        "RAMPI_RUST_MIXED_SOAK_OK\nRAMPI_MIXED_SOAK_SERVER_RECEIPTS_OK\n"
    )
    (tmp_path / "keyboard-receipts.txt").write_text("\n".join(tokens))
    return tmp_path


def test_complete_workload(evidence):
    assert MODULE.check(evidence)["cycles"] == 150


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("duration_seconds", 59),
        ("cycles", 1),
        ("module_switches", 1049),
        ("live_ptys", 0),
        ("webkit_javascript_roundtrips", 149),
        ("distinct_remote_pixel_hashes", 1),
        ("swap_limit_bytes", 1024**3),
        ("memory_limit_bytes", 2 * 1024**3),
        ("switch_p95_paint_ms", float("nan")),
        ("cgroup_peak_memory_bytes", 1024**3),
        ("final_memory_bytes", 600 * 1024**2),
        ("binary_sha256", "stale"),
        ("samples", []),
        ("remote_input_tokens", []),
    ],
)
def test_reject_incomplete_or_invalid_workload(evidence, key, value):
    path = evidence / "mixed-soak.json"
    report = json.loads(path.read_text())
    report[key] = value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        MODULE.check(evidence)


def test_reject_missing_actual_server_input(evidence):
    (evidence / "keyboard-receipts.txt").write_text("rampisoak0\n")
    with pytest.raises(ValueError, match="Server-confirmed"):
        MODULE.check(evidence)
