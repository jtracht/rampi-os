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
from gi.repository import Atspi  # noqa: E402

# Keep ordinary calls at the library default; bound startup probes of stale
# optional objects without changing the enclosing page/readiness deadlines.
Atspi.set_timeout(800, 2000)


def visible_objects():
    visited = 0

    def walk(node, depth=0):
        nonlocal visited
        if depth > 20 or visited >= 5000:
            return
        visited += 1
        try:
            state = node.getState()
            if depth > 1 and not state.contains(pyatspi.STATE_SHOWING):
                return
            yield node, state
            for child in node:
                yield from walk(child, depth + 1)
        except Exception:
            # A disappearing or unsupported subtree cannot supply required data.
            return

    yield from walk(pyatspi.Registry.getDesktop(0))


def snapshot():
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


def main():
    if sys.argv[1:] == ["--fixture-profile-text"]:
        account = pwd.getpwuid(os.getuid())
        if account.pw_name not in {"rampi-hid-one", "rampi-hid-two"} or account.pw_uid < 1000:
            raise SystemExit("Only the designated synthetic HID account field may be read")
        field = next(
            (
                node
                for node, _ in visible_objects()
                if node.getRoleName() in {"text", "entry"} and node.name == "Profilname"
            ),
            None,
        )
        if field is None:
            raise SystemExit("Actual synthetic profile field unavailable")
        text = field.queryText()
        print(json.dumps(text.getText(0, text.characterCount), ensure_ascii=False))
        return
    if sys.argv[1:]:
        raise SystemExit("Unsupported accessibility fixture mode")
    for _ in range(50):
        rows = snapshot()
        if any(row["role"] == "frame" and row["name"] == "Rampi" for row in rows):
            print(json.dumps(rows, ensure_ascii=False))
            break
        time.sleep(0.1)
    else:
        raise SystemExit("Actual Rampi accessibility tree is missing")


if __name__ == "__main__":
    main()
