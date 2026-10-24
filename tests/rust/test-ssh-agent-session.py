"""Actual OpenSSH agent ownership; only the final compositor handoff is a fixture."""

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable container required")


def reachable(path):
    result = subprocess.run(
        ["/usr/bin/ssh-add", "-l"],
        env={**os.environ, "SSH_AUTH_SOCK": path},
        capture_output=True,
        timeout=4,
    )
    return result.returncode in (0, 1)


with tempfile.TemporaryDirectory(prefix="rampi-agent-") as directory:
    root = Path(directory)
    session = root / "session"
    handoff = root / "handoff"
    handoff.write_text('#!/bin/sh\nprintf "%s\\n" "$SSH_AUTH_SOCK"\nread -r finish\n')
    handoff.chmod(0o700)
    session.write_text(
        Path("system/rampi-session")
        .read_text()
        .replace("/usr/local/bin/rampi-session", str(session))
        .replace("/usr/local/bin/rampi-wayland-start", str(handoff))
    )
    session.chmod(0o700)

    def exercise(sock=None):
        env = {**os.environ, "WAYLAND_DISPLAY": "fixture-handoff-only"}
        for name in ["SSH_AUTH_SOCK", "SSH_AGENT_PID", "RAMPI_AGENT_ATTEMPTED"]:
            env.pop(name, None)
        if sock:
            env["SSH_AUTH_SOCK"] = sock
        process = subprocess.Popen(
            [str(session)],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            actual = process.stdout.readline().strip()
            assert actual and reachable(actual), "Graphical session received no reachable agent"
            if sock and reachable(sock):
                assert actual == sock, "Existing agent was replaced"
            process.communicate("\n", timeout=5)
            assert process.returncode == 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        return actual

    for supplied in [None, str(root / "stale-socket")]:
        owned = exercise(supplied)
        deadline = time.monotonic() + 15
        while reachable(owned) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not reachable(owned), "Session-owned agent survived its session"
    info = subprocess.check_output(["/usr/bin/ssh-agent", "-s"], text=True)
    foreign_socket = re.search(r"SSH_AUTH_SOCK=([^;]+);", info)[1]
    foreign_pid = int(re.search(r"SSH_AGENT_PID=(\d+);", info)[1])
    try:
        assert exercise(foreign_socket) == foreign_socket
        assert reachable(foreign_socket), "Rampi stopped a pre-existing agent"
    finally:
        os.kill(foreign_pid, 15)
print("RAMPI_RUST_SSH_AGENT_LIFETIME_OK")
