"""Real AccountsService and PAM integration, confined to a throwaway container."""

import os
import pwd
import subprocess
import uuid
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from rampi.accounts import create_user

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Account mutation tests may run only in the designated disposable container")
if os.geteuid() != 0:
    raise SystemExit("This isolated integration test needs container root")
app = QCoreApplication([])
Path("/run/dbus").mkdir(parents=True, exist_ok=True)
subprocess.run(["dbus-daemon", "--system", "--fork"], check=True)
username = "rampitest" + uuid.uuid4().hex[:10]
password = uuid.uuid4().hex + "-Aa7!"
create_user(username, "Rampi container integration", password)
account = pwd.getpwnam(username)
if account.pw_uid == 0:
    raise SystemExit("Created account unexpectedly has root identity")
Path("/etc/pam.d/rampi-ci").write_text("auth required pam_unix.so\naccount required pam_unix.so\n")
for supplied, expected in [(password, 0), (uuid.uuid4().hex, 1)]:
    result = subprocess.run(
        ["pamtester", "rampi-ci", username, "authenticate"],
        input=supplied + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if (result.returncode == 0) != (expected == 0):
        raise SystemExit("Native PAM password verification did not match the expected outcome")
print(
    "PASS: real AccountsService created a non-root account; "
    "PAM accepts its password and rejects an incorrect one."
)
