"""Read visible GTK accessibility metadata inside the disposable HID fixture."""

import json
import os
import pwd
import subprocess
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    if not Path("/etc/rampi-acceptance-vm").is_file():
        raise SystemExit("Designated QEMU fixture required")
    subprocess.run(["systemd-detect-virt", "--vm", "--quiet"], check=True)

import pyatspi  # noqa: E402
from gi.repository import Atspi, GLib  # noqa: E402

# Bound library calls separately from a complete read. The enclosing page
# predicate retains its existing readiness deadline.
Atspi.set_timeout(800, 2000)
READ_BUDGET = 45


class TreeReadUnavailable(RuntimeError):
    """A fresh complete accessibility read could not finish within its budget."""


def visible_objects():
    deadline = time.monotonic() + READ_BUDGET
    seen = set()

    def check_budget():
        if time.monotonic() >= deadline:
            raise TreeReadUnavailable("read-budget")

    def walk(node, depth=0):
        check_budget()
        if node in seen:
            return
        if depth > 20:
            raise TreeReadUnavailable("depth-limit")
        if len(seen) >= 5000:
            raise TreeReadUnavailable("node-limit")
        seen.add(node)
        try:
            state = node.getState()
            check_budget()
            if depth > 1 and not state.contains(pyatspi.STATE_SHOWING):
                return
            yield node, state
            for child in node:
                check_budget()
                yield from walk(child, depth + 1)
        except TreeReadUnavailable:
            raise
        except Exception:
            # A disappearing or unsupported subtree cannot supply required data.
            return

    yield from walk(pyatspi.Registry.getDesktop(0))


def snapshot():
    try:
        return [
            {
                "role": node.getRoleName(),
                "name": node.name or "",
                "enabled": state.contains(pyatspi.STATE_ENABLED),
                "sensitive": state.contains(pyatspi.STATE_SENSITIVE),
                "states": [str(value) for value in state.getStates()],
            }
            for node, state in visible_objects()
        ]
    except (GLib.GError, TreeReadUnavailable) as error:
        reason = str(error) if isinstance(error, TreeReadUnavailable) else "stale-object"
        print("A11Y_READ_UNAVAILABLE " + reason, file=sys.stderr, flush=True)
        # Reconnecting can invalidate a proxy between enumeration and reading.
        # Return no required data; the enclosing readiness check must obtain a
        # complete new snapshot within its unchanged deadline. Never reuse rows.
        return []


def read_controls(caption, roles, *, sensitive=False):
    # Retry only read-side stale proxies. Resolve the named control before
    # performing any action, so a delayed acknowledgement never clicks twice.
    deadline = time.monotonic() + READ_BUDGET
    while True:
        try:
            return [
                node
                for node, state in visible_objects()
                if node.name == caption
                and node.getRoleName() in roles
                and (not sensitive or state.contains(pyatspi.STATE_SENSITIVE))
            ]
        except (GLib.GError, TreeReadUnavailable):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


def activate_control(caption):
    matches = read_controls(caption, {"button"}, sensitive=True)
    if len(matches) != 1 or not matches[0].queryAction().doAction(0):
        raise RuntimeError("Unique visible GTK button action unavailable: " + caption)


def control_bounds(caption):
    matches = read_controls(caption, {"text", "entry", "password text"})
    if len(matches) != 1:
        raise RuntimeError("Unique visible GTK field unavailable: " + caption)
    # Wayland does not publish global widget positions (GTK reports 0/0).
    # The designated Rampi fixture is fullscreen at the output origin.
    bounds = matches[0].queryComponent().getExtents(pyatspi.WINDOW_COORDS)
    if bounds.width <= 0 or bounds.height <= 0 or bounds.x < 0 or bounds.y < 0:
        raise RuntimeError("Actual visible GTK field bounds unavailable")
    return {key: getattr(bounds, key) for key in ["x", "y", "width", "height"]}


def main():
    if sys.argv[1:]:
        account = pwd.getpwuid(os.getuid())
        if account.pw_name not in {"rampi-hid-one", "rampi-hid-two"} or account.pw_uid < 1000:
            raise SystemExit("Only the designated synthetic HID accounts may control the fixture")
    if len(sys.argv) == 3 and sys.argv[1] == "--fixture-activate":
        activate_control(sys.argv[2])
        print(json.dumps({"activated": True}))
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--fixture-control-bounds":
        print(json.dumps(control_bounds(sys.argv[2])))
        return
    if sys.argv[1:] == ["--fixture-profile-text"]:
        account = pwd.getpwuid(os.getuid())
        if account.pw_name not in {"rampi-hid-one", "rampi-hid-two"} or account.pw_uid < 1000:
            raise SystemExit("Only the designated synthetic HID account field may be read")
        matches = read_controls("Profilname", {"text", "entry"})
        if len(matches) != 1:
            raise SystemExit("Unique actual synthetic profile field unavailable")
        field = matches[0]
        text = field.queryText()
        print(json.dumps(text.getText(0, text.characterCount), ensure_ascii=False))
        return
    if sys.argv[1:]:
        raise SystemExit("Unsupported accessibility fixture mode")
    # The enclosing page predicate owns readiness and its existing deadline.
    # One failed read supplies no data; do not nest fifty potentially slow scans
    # inside a single helper invocation or retain any rows from an earlier scan.
    rows = snapshot()
    current_frame = any(row["role"] == "frame" and row["name"] == "Rampi" for row in rows)
    print(json.dumps(rows if current_frame else [], ensure_ascii=False))



if __name__ == "__main__":
    main()
