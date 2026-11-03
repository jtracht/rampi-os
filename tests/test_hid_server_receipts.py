"""Independent receipt corruption and real fixture readiness callback controls."""

import ast
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
verify = runpy.run_path(str(ROOT / "scripts/check-hid-rdp-evidence.py"))[
    "verify_server_receipts"
]
NONCE = "a" * 32
EVENTS = [{"kind": "press", "button": 1}, {"kind": "release", "button": 1}]


@pytest.fixture
def receipts(tmp_path):
    directory = tmp_path / "server-receipts/fixture-user"
    directory.mkdir(parents=True)
    (directory / "input.txt").write_text("q\n€\n", encoding="utf-8")
    for name in ["nonce.txt", "ready.txt"]:
        (directory / name).write_text(NONCE)
    (directory / "events.jsonl").write_text("\n".join(map(json.dumps, EVENTS)))
    return tmp_path, directory


def check(receipts):
    verify(receipts[0], "fixture-user", ["q", "€"], NONCE, EVENTS)


def test_nonhidden_independent_receipts_are_verifiable(receipts):
    check(receipts)
    assert all(not p.name.startswith(".") for p in receipts[1].iterdir())


@pytest.mark.parametrize("name", ["input.txt", "nonce.txt", "ready.txt", "events.jsonl"])
def test_missing_export_is_not_silently_accepted(receipts, name):
    (receipts[1] / name).unlink()
    with pytest.raises(FileNotFoundError):
        check(receipts)


@pytest.mark.parametrize("name", ["input.txt", "nonce.txt", "ready.txt"])
def test_different_server_input_identity_or_readiness_is_rejected(receipts, name):
    (receipts[1] / name).write_text("different")
    with pytest.raises(ValueError):
        check(receipts)


def test_reserved_shortcut_after_reported_events_is_also_rejected(receipts):
    with (receipts[1] / "events.jsonl").open("a") as stream:
        stream.write('\n{"kind":"key","key":"Home"}\n')
    with pytest.raises(ValueError, match="Reserved shortcut"):
        check(receipts)


def test_reordered_mouse_receipts_are_rejected(receipts):
    (receipts[1] / "events.jsonl").write_text("\n".join(map(json.dumps, EVENTS[::-1])))
    with pytest.raises(ValueError, match="mouse/key events differ"):
        check(receipts)


@pytest.mark.parametrize("mapped,focused", [(False, False), (False, True), (True, False),
                                          (True, True)])
def test_actual_fixture_callback_requires_mapping_and_observed_focus(tmp_path, mapped, focused):
    tree = ast.parse((ROOT / "tests/rust/test-rdp.py").read_text())
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                 and n.name == "publish_input_ready"]
    assert len(functions) == 1
    entry, pending = object(), []
    # There is deliberately no focus_force method: the observer must not repair focus.
    root = SimpleNamespace(winfo_ismapped=lambda: mapped,
                           focus_get=lambda: entry if focused else None,
                           after=lambda delay, callback: pending.append((delay, callback)))
    scope = {"root": root, "entry": entry, "nonce": NONCE,
             "receipt_path": lambda name: tmp_path / name}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "fixture-readiness", "exec"), scope)  # noqa: S102 - trusted repository callback, no external code
    scope["publish_input_ready"]()
    path = tmp_path / ".rampi-ready"
    assert path.exists() is (mapped and focused)
    if path.exists():
        assert path.read_text() == NONCE
        assert pending == []
    else:
        assert len(pending) == 1 and pending[0][0] > 0
