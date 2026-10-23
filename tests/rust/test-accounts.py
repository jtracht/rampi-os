"""Actual unprivileged GTK/VTE passwd and PAM, confined to one disposable container."""

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

if (
    os.environ.get("RAMPI_TEST_CONTAINER") != "1"
    or not Path("/.dockerenv").exists()
    or os.geteuid() != 0
):
    raise SystemExit("Disposable container root required")

with tempfile.TemporaryDirectory(prefix="rampi-account-") as directory:
    root = Path(directory)
    root.chmod(0o755)
    old, new = (uuid.uuid4().hex + "-Aa7!" for _ in range(2))
    subprocess.run(["chpasswd"], input=f"rampi:{old}\n", text=True, check=True)
    secrets = root / "fixture.json"
    secrets.write_text(json.dumps({"old": old, "new": new}))
    secrets.chmod(0o600)
    os.chown(secrets, 1000, 1000)
    prefix = (
        Path("tests/rust/run-wayland.sh").read_text().split("bash tests/rust/test-first-run.sh")[0]
    )
    script = root / "session.sh"
    script.write_text(prefix + "timeout 40 /build/target/debug/rampi-native --account-ui-check\n")
    result = subprocess.run(
        ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", str(script)],
        env={**os.environ, "LC_ALL": "C", "RAMPI_TEST_ACCOUNT_FILE": str(secrets)},
        capture_output=True,
        text=True,
        timeout=50,
    )
    if old in result.stdout + result.stderr or new in result.stdout + result.stderr:
        raise RuntimeError("A password appeared in terminal output")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    assert "RAMPI_RUST_ACCOUNT_PAGE_OK" in result.stdout
    Path("/etc/pam.d/rampi-ci").write_text(
        "auth required pam_unix.so\naccount required pam_unix.so\n"
    )
    for supplied, expected in [(old, False), (uuid.uuid4().hex, False), (new, True)]:
        authentication = subprocess.run(
            ["pamtester", "rampi-ci", "rampi", "authenticate"],
            input=supplied + "\n",
            text=True,
            capture_output=True,
            timeout=15,
        )
        assert (authentication.returncode == 0) == expected, "Actual PAM outcome mismatch"
    subprocess.run(["useradd", "--create-home", "rampi-other"], check=True)
    denied = subprocess.run(
        ["runuser", "-u", "rampi-other", "--", "cat", str(secrets)], capture_output=True
    )
    assert denied.returncode != 0 and not denied.stdout, (
        "Another Linux user read private credentials"
    )
    print(result.stdout.strip())
print("RAMPI_RUST_ACCOUNT_PAM_OK")
print(
    "PASS: real unprivileged passwd, PAM old/wrong/new authentication and Linux file isolation; "
    "no graphical greetd login proof."
)
