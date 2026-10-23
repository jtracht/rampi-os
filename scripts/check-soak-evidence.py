"""Validate the actual ten-minute RDP/WebKit/PTY software workload evidence."""

import argparse
import json
import math
import re
from pathlib import Path


def check(directory: Path):
    report = json.loads((directory / "mixed-soak.json").read_text(encoding="utf-8"))
    log = (directory / "acceptance.log").read_text(encoding="utf-8")
    for marker in ["RAMPI_RUST_MIXED_SOAK_OK", "RAMPI_MIXED_SOAK_SERVER_RECEIPTS_OK"]:
        if marker not in log:
            raise ValueError("Missing mixed workload stage: " + marker)
    for key in ["duration_seconds", "switch_p95_paint_ms", "cgroup_cpu_percent_of_one_core"]:
        if not isinstance(report.get(key), (int, float)) or not math.isfinite(report[key]):
            raise ValueError("Invalid measured value: " + key)
    cycles = report.get("cycles", 0)
    if type(cycles) is not int or cycles < 100 or report["duration_seconds"] < 600:
        raise ValueError("Mixed workload did not run for ten minutes")
    if report.get("module_switches") != cycles * 7:
        raise ValueError("Module paints missing")
    if report.get("live_ptys") != 3 or report.get("webkit_javascript_roundtrips") != cycles:
        raise ValueError("Browser or live PTY workload missing")
    if not 30 <= report.get("distinct_remote_pixel_hashes", 0) <= cycles:
        raise ValueError("Changing remote frames missing")
    if not 0 < report["switch_p95_paint_ms"] < 500:
        raise ValueError("Software paint latency exceeded budget")
    if not 0 < report["cgroup_cpu_percent_of_one_core"] <= 405:
        raise ValueError("Invalid cgroup CPU accounting")
    if not re.fullmatch(r"[a-f0-9]{64}", report.get("binary_sha256", "")):
        raise ValueError("Actual executable digest missing")
    limit = 1024**3
    if report.get("memory_limit_bytes") != limit or report.get("swap_limit_bytes") != 0:
        raise ValueError("Resource limit or swap proof missing")
    peak, warm, final = [
        report.get(key, 0)
        for key in ["cgroup_peak_memory_bytes", "warm_memory_bytes", "final_memory_bytes"]
    ]
    if not 0 < warm <= peak < 1000 * 1024**2 or not 0 < final <= peak:
        raise ValueError("Memory headroom missing")
    if final >= warm + 128 * 1024**2:
        raise ValueError("Memory grew after warm-up")
    samples = report.get("samples", [])
    if len(samples) != cycles:
        raise ValueError("Periodic memory samples missing")
    previous = 0
    for sample in samples:
        elapsed = sample.get("elapsed_seconds", 0)
        if not previous < elapsed <= report["duration_seconds"]:
            raise ValueError("Invalid sample chronology")
        if not 0 < sample.get("cgroup_memory_bytes", 0) <= peak:
            raise ValueError("Invalid memory sample")
        previous = elapsed
    if previous < 590:
        raise ValueError("Samples ended before workload completion")
    receipts = (directory / "keyboard-receipts.txt").read_text(encoding="utf-8").splitlines()
    expected = [f"rampisoak{cycle}" for cycle in range(0, cycles, 15)]
    if report.get("remote_input_tokens") != expected or any(
        token not in receipts for token in expected
    ):
        raise ValueError("Server-confirmed input throughout the workload is missing")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    options = parser.parse_args()
    check(options.directory)
    print(
        "PASS: ten-minute mixed native workload, changing remote pixels and server input receipts."
    )
