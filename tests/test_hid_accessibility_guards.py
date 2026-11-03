"""Fast failure controls for the real fixture helper, not graphical acceptance."""

import json
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

HELPER = Path(__file__).resolve().parents[1] / "scripts/virtual/hid-accessible-state.py"


class StaleObjectError(Exception):
    pass


class Clock:
    now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class State:
    def __init__(self, flags=(1, 2, 3)):
        self.flags = flags

    def contains(self, flag):
        return flag in self.flags

    def getStates(self):
        return list(self.flags)


class Node:
    def __init__(self, name="Rampi", role="frame", flags=(1, 2, 3)):
        self.name, self.role, self.state = name, role, State(flags)
        self.children = []
        self.state_reads = self.actions = self.stale_reads = 0
        self.action_error = False
        self.action_result = True
        self.bounds = SimpleNamespace(x=12, y=34, width=150, height=25)

    def getState(self):
        self.state_reads += 1
        return self.state

    def getRoleName(self):
        if self.stale_reads:
            self.stale_reads -= 1
            raise StaleObjectError("Controlled stale external proxy")
        return self.role

    def __iter__(self):
        return iter(self.children)

    def queryAction(self):
        return self

    def doAction(self, _index):
        self.actions += 1
        if self.action_error:
            raise StaleObjectError("Controlled uncertain action acknowledgement")
        return self.action_result

    def queryComponent(self):
        return self

    def getExtents(self, coordinates):
        self.coordinates = coordinates
        return self.bounds


@pytest.fixture
def helper(monkeypatch):
    # Exercise helper decisions on all CI operating systems without installing
    # or pretending to run Linux AT-SPI/GTK. Real GTK/QEMU gates remain separate.
    clock, root = Clock(), Node()
    atspi = SimpleNamespace(set_timeout=lambda *_: None)
    gi = ModuleType("gi")
    repository = ModuleType("gi.repository")
    repository.Atspi = atspi
    repository.GLib = SimpleNamespace(GError=StaleObjectError)
    gi.repository = repository
    api = ModuleType("pyatspi")
    api.Registry = SimpleNamespace(getDesktop=lambda _: root)
    api.STATE_SHOWING, api.STATE_ENABLED, api.STATE_SENSITIVE = 1, 2, 3
    api.WINDOW_COORDS = object()
    for name, module in [("gi", gi), ("gi.repository", repository), ("pyatspi", api)]:
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setitem(sys.modules, "pwd", SimpleNamespace())
    loaded = runpy.run_path(str(HELPER))
    scope = loaded["snapshot"].__globals__
    scope["time"] = clock
    return SimpleNamespace(scope=scope, root=root, clock=clock, api=api)


def test_cycle_and_shared_alias_are_read_once(helper):
    child = Node("Target", "button")
    helper.root.children = [child, child, helper.root]
    assert len(helper.scope["snapshot"]()) == 2
    assert child.state_reads == helper.root.state_reads == 1


def test_expired_read_discards_earlier_valid_rows(helper, capsys):
    child = Node("Too late", "button")
    helper.root.children = [child]

    def delayed_state():
        helper.clock.now += helper.scope["READ_BUDGET"] + 1
        return State()

    child.getState = delayed_state
    assert helper.scope["snapshot"]() == []
    assert "read-budget" in capsys.readouterr().err


def test_transient_read_can_recover_before_one_action(helper):
    node = Node("Target", "button")
    node.stale_reads = 1
    helper.root.children = [node]
    helper.scope["activate_control"]("Target")
    assert node.actions == 1
    assert node.stale_reads == 0


def test_stale_snapshot_discards_previous_valid_rows(helper, capsys):
    node = Node("Target", "button")
    node.stale_reads = 1
    helper.root.children = [node]
    assert helper.scope["snapshot"]() == []
    assert "stale-object" in capsys.readouterr().err


def test_permanent_stale_control_read_expires_without_action(helper):
    node = Node("Target", "button")
    node.stale_reads = 1_000_000
    helper.root.children = [node]
    with pytest.raises(StaleObjectError):
        helper.scope["activate_control"]("Target")
    assert node.actions == 0
    assert helper.clock.now >= helper.scope["READ_BUDGET"]


def test_excessive_tree_depth_discards_partial_snapshot(helper, capsys):
    parent = helper.root
    for _ in range(22):
        child = Node()
        parent.children = [child]
        parent = child
    assert helper.scope["snapshot"]() == []
    assert "depth-limit" in capsys.readouterr().err


def test_uncertain_action_is_never_retried(helper):
    node = Node("Target", "button")
    node.action_error = True
    helper.root.children = [node]
    with pytest.raises(StaleObjectError, match="uncertain"):
        helper.scope["activate_control"]("Target")
    assert node.actions == 1


def test_duplicate_buttons_cannot_trigger_either_action(helper):
    nodes = [Node("Target", "button"), Node("Target", "button")]
    helper.root.children = nodes
    with pytest.raises(RuntimeError, match="Unique visible GTK button"):
        helper.scope["activate_control"]("Target")
    assert all(node.actions == 0 for node in nodes)


def test_insensitive_button_cannot_be_activated(helper):
    node = Node("Target", "button", flags=(1, 2))
    helper.root.children = [node]
    with pytest.raises(RuntimeError, match="Unique visible GTK button"):
        helper.scope["activate_control"]("Target")
    assert node.actions == 0


def test_negative_action_acknowledgement_fails_without_replay(helper):
    node = Node("Target", "button")
    node.action_result = False
    helper.root.children = [node]
    with pytest.raises(RuntimeError):
        helper.scope["activate_control"]("Target")
    assert node.actions == 1


def test_field_uses_window_coordinates_not_wayland_global_origin(helper):
    node = Node("Profilname", "text")
    helper.root.children = [node]
    assert helper.scope["control_bounds"]("Profilname") == {
        "x": 12,
        "y": 34,
        "width": 150,
        "height": 25,
    }
    assert node.coordinates is helper.api.WINDOW_COORDS


@pytest.mark.parametrize("attribute,value", [("width", 0), ("height", -1), ("x", -1)])
def test_invalid_field_rectangle_is_rejected(helper, attribute, value):
    node = Node("Profilname", "text")
    setattr(node.bounds, attribute, value)
    helper.root.children = [node]
    with pytest.raises(RuntimeError, match="field bounds unavailable"):
        helper.scope["control_bounds"]("Profilname")


@pytest.mark.parametrize("current_frame", [False, True])
def test_cli_reads_once_and_requires_current_frame(helper, monkeypatch, capsys, current_frame):
    calls = []

    def read():
        calls.append(True)
        return [{"role": "frame", "name": "Rampi" if current_frame else "Old application"}]

    helper.scope["snapshot"] = read
    monkeypatch.setattr(sys, "argv", ["fixture-helper"])
    helper.scope["main"]()
    rows = json.loads(capsys.readouterr().out)
    assert bool(rows) is current_frame
    assert calls == [True]


def test_peer_row_uses_current_label_bounds(helper):
    node = Node("Pinned SDK · 00:AA:01:01:00:01 · Verbunden", "label")
    helper.root.children = [node]
    assert helper.scope["peer_bounds"]("00:AA:01:01:00:01")["x"] == 12
    assert node.coordinates is helper.api.WINDOW_COORDS


def test_ambiguous_or_wrong_peer_is_not_selected(helper):
    helper.root.children = [Node("SDK · 00:AA:01:01:00:01", "label") for _ in range(2)]
    with pytest.raises(RuntimeError, match="Unique visible"):
        helper.scope["peer_bounds"]("00:AA:01:01:00:01")
    with pytest.raises(RuntimeError, match="Only the pinned"):
        helper.scope["peer_bounds"]("11:22:33:44:55:66")
