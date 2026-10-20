"""Exercise the real personal Secret Service in an isolated D-Bus session."""

import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

from rampi.kanban import secret, store_token

with tempfile.TemporaryDirectory(prefix="rampi-keyring-test-") as name:
    directory = Path(name)
    for setting, child in [("XDG_DATA_HOME", "data"), ("XDG_RUNTIME_DIR", "runtime")]:
        path = directory / child
        path.mkdir(mode=0o700)
        os.environ[setting] = str(path)
    daemon = subprocess.Popen(
        ["gnome-keyring-daemon", "--unlock", "--components=secrets", "--foreground"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if daemon.stdin is None:
            raise SystemExit("Keyring password pipe missing")
        daemon.stdin.write(secrets.token_bytes(32).hex().encode())
        daemon.stdin.close()
        for _ in range(50):
            ready = subprocess.run(
                ["busctl", "--user", "status", "org.freedesktop.secrets"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise SystemExit("Secret Service failed to start")
        sample = secrets.token_urlsafe(32)
        store_token("integration", "github", "", sample)
        if secret("integration") != sample:
            raise SystemExit("Secret Service roundtrip failed")
        keyrings = list((directory / "data/keyrings").glob("*.keyring"))
        if not keyrings or any(path.stat().st_mode & 0o077 for path in keyrings):
            raise SystemExit("Personal keyring missing or accessible to another user")
        if any(sample.encode() in path.read_bytes() for path in keyrings):
            raise SystemExit("Unencrypted credential found in keyring file")
        print("PASS: real GNOME Keyring store/lookup; encrypted file and user-only permissions.")
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)
