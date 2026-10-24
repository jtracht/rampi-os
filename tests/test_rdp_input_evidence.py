"""Synthetic guard tests for rejecting incomplete evidence; not runtime acceptance."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "rdp_input_evidence",
    Path(__file__).resolve().parents[1] / "scripts/check-rdp-input-evidence.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def evidence(tmp_path):
    report = {
        "schema": 1,
        "probe": "a" * 32,
        "remote_size": [1920, 1080],
        "scale": 0.5,
        "local_delta": [30, 20],
        "clipboard_roundtrips": 2,
        "gtk_scroll_deltas": [[0, 15], [0, -15], [15, 0], [-15, 0]],
    }
    events = []
    for button in range(1, 8):
        x, y = (960, 540) if button == 1 else (1020, 580)
        events += [
            {"kind": "press", "button": button, "x": x, "y": y},
            {"kind": "release", "button": button},
        ]
    events += [
        {"kind": "clipboard", "text": f"rampi-local-{'a' * 32}-{n}-Grüße 🥧\nsecond line"}
        for n in range(2)
    ]
    (tmp_path / "rdp-input.json").write_text(json.dumps(report), encoding="utf-8")
    (tmp_path / "remote-events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events), encoding="utf-8"
    )
    (tmp_path / "keyboard-receipts.txt").write_text("rampirdp0\nrampiafterhome\nrampirdp1\n")
    return tmp_path


def test_accept_complete_receipt_structure(evidence):
    assert MODULE.check(evidence)["clipboard_roundtrips"] == 2


def test_accept_actual_tk_shift_wheel_representation(evidence):
    path = evidence / "remote-events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    for event in events:
        if event.get("button") in (6, 7):
            event["button"] -= 2
            event["state"] = 1
    path.write_text("\n".join(json.dumps(e) for e in events))
    assert MODULE.check(evidence)


def test_reject_horizontal_receipts_without_shift_or_horizontal_button(evidence):
    path = evidence / "remote-events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    for event in events:
        if event.get("button") in (6, 7):
            event["button"] -= 2
    path.write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="two-axis"):
        MODULE.check(evidence)


@pytest.mark.parametrize(
    "change", ["button", "release", "scroll", "coordinates", "shortcut", "clipboard", "keyboard"]
)
def test_reject_missing_actual_receipts(evidence, change):
    path = evidence / "remote-events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    if change in {"button", "release", "scroll"}:
        kind, button = (
            ("release", 2) if change == "release" else ("press", 6 if change == "scroll" else 1)
        )
        events = [e for e in events if not (e["kind"] == kind and e.get("button") == button)]
    elif change == "coordinates":
        events[0]["x"] = 100
    elif change == "shortcut":
        events += [{"kind": "key", "key": "Home"}]
    elif change == "clipboard":
        events.pop()
    else:
        (evidence / "keyboard-receipts.txt").write_text("rampirdp0\nrampirdp1\n")
    path.write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError):
        MODULE.check(evidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("probe", ""),
        ("scale", float("nan")),
        ("scale", 0),
        ("remote_size", [0, 0]),
        ("clipboard_roundtrips", 1),
        ("local_delta", [0, 0]),
    ],
)
def test_reject_wrong_report(evidence, field, value):
    path = evidence / "rdp-input.json"
    report = json.loads(path.read_text())
    report[field] = value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        MODULE.check(evidence)
