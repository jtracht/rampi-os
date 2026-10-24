"""Validate downloaded actual XRDP input receipts, scaling and Unicode roundtrips."""

import argparse
import json
import math
import re
from pathlib import Path


def check(directory: Path):
    report = json.loads((directory / "rdp-input.json").read_text(encoding="utf-8"))
    probe = report.get("probe", "")
    if (
        type(report.get("schema")) is not int
        or report["schema"] != 1
        or not isinstance(probe, str)
        or not re.fullmatch(r"[a-f0-9]{32}", probe)
    ):
        raise ValueError("Missing actual RDP probe identity")
    dimensions = report.get("remote_size")
    scale = report.get("scale")
    if (
        not isinstance(dimensions, list)
        or len(dimensions) != 2
        or not all(type(n) is int and 320 <= n <= 8192 for n in dimensions)
        or type(scale) not in (int, float)
        or not math.isfinite(scale)
        or not 0.05 < scale <= 8
        or report.get("local_delta") != [30, 20]
        or report.get("clipboard_roundtrips") != 2
    ):
        raise ValueError("Invalid actual desktop dimensions or clipboard report")
    events = [
        json.loads(line)
        for line in (directory / "remote-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for kind in ["press", "release"]:
        buttons = {row.get("button") for row in events if row.get("kind") == kind}
        if not {1, 2, 3}.issubset(buttons):
            raise ValueError("Missing actual three-button receipts: " + kind)
        # The actual Tk/X11 receiver can represent horizontal scrolling as
        # Shift+button4/5, or as button6/7. Preserve and inspect raw event state.
        vertical = {
            e.get("button")
            for e in events
            if e.get("kind") == kind and e.get("button") in (4, 5) and not e.get("state", 0) & 1
        }
        horizontal = {
            e["button"] - 2 if e["button"] in (6, 7) else e["button"]
            for e in events
            if e.get("kind") == kind
            and (e.get("button") in (6, 7) or e.get("button") in (4, 5) and e.get("state", 0) & 1)
        }
        if vertical != {4, 5} or horizontal != {4, 5}:
            raise ValueError("Missing actual two-axis scroll receipts: " + kind)
    scrolls = report.get("gtk_scroll_deltas", [])
    if not isinstance(scrolls, list) or not all(
        isinstance(event, list)
        and len(event) == 2
        and all(type(n) in (int, float) and math.isfinite(n) for n in event)
        for event in scrolls
    ):
        raise ValueError("Invalid actual GTK scroll event data")
    if not all(
        any(
            (x * sign > 0 and y == 0) if axis == 0 else (y * sign > 0 and x == 0)
            for x, y in scrolls
        )
        for axis in (0, 1)
        for sign in (-1, 1)
    ):
        raise ValueError("Actual GTK scrolling did not cover both axes and directions")
    width, height = dimensions
    expected = [(width / 2, height / 2), (width / 2 + 30 / scale, height / 2 + 20 / scale)]
    for button, point in [(1, expected[0]), (2, expected[1]), (3, expected[1])]:
        if not any(
            row.get("kind") == "press"
            and row.get("button") == button
            and abs(row.get("x", -10000) - point[0]) <= 8
            and abs(row.get("y", -10000) - point[1]) <= 8
            for row in events
        ):
            raise ValueError("Scaled remote mouse coordinates differ from actual GTK input")
    if any(row.get("kind") == "key" and row.get("key") == "Home" for row in events):
        raise ValueError("Reserved Rampi shortcut reached the remote desktop")
    receipts = (directory / "keyboard-receipts.txt").read_text(encoding="utf-8").splitlines()
    if not {"rampirdp0", "rampirdp1", "rampiafterhome"}.issubset(receipts):
        raise ValueError("Remote keyboard/reconnect/module-return receipt missing")
    clips = {row.get("text") for row in events if row.get("kind") == "clipboard"}
    if not {
        f"rampi-local-{probe}-{roundtrip}-Grüße 🥧\nsecond line" for roundtrip in range(2)
    }.issubset(clips):
        raise ValueError("Actual remote Unicode clipboard receipt missing")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
    print("PASS: actual scaled XRDP input, reserved shortcut and Unicode clipboard receipts.")
