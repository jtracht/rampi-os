"""Validate measured GTK frame work, without claiming Raspberry Pi frame timing."""

import argparse
import json
import math
from pathlib import Path


def check(directory, expected_binary):
    proof = json.loads((directory / "animation-scheduling.json").read_text(encoding="utf-8"))
    if (type(proof.get("schema")) is not int or proof["schema"] != 1
            or proof.get("native_elf_sha256") != expected_binary
            or proof.get("single_window") is not True
            or proof.get("complete_product_acceptance") is not False):
        raise ValueError("Actual animation executable/window/scope evidence missing")
    for key in ["idle_ticks", "reduced_ticks"]:
        if type(proof.get(key)) is not int or proof[key] != 0:
            raise ValueError("Idle or reduced-motion callbacks did not stop: " + key)
    paints = proof.get("active_paints")
    window = proof.get("active_window_ms")
    if (type(window) not in [int, float] or not math.isfinite(window)
            or not 500 <= window <= 5000):
        raise ValueError("Actual measured animation observation window missing")
    if type(paints) is not int or not 2 <= paints <= math.ceil(window * 31 / 1000) + 2:
        raise ValueError("Actual active software surface paint budget failed")
    if not isinstance(proof.get("scope"), str) or "not Raspberry Pi timing" not in proof["scope"]:
        raise ValueError("Virtual evidence must disclose its timing scope")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary", required=True)
    args = parser.parse_args()
    check(args.directory, args.expected_binary)
