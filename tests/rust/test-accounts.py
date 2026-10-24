"""Actual unprivileged GTK/VTE passwd and PAM, confined to one disposable container."""

import json
import os
import pwd
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
    old, new, created = (uuid.uuid4().hex + "-Aa7!" for _ in range(3))
    subprocess.run(["chpasswd"], input=f"rampi:{old}\n", text=True, check=True)
    secrets = root / "fixture.json"
    secrets.write_text(json.dumps({"old": old, "new": new, "created": created}))
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
    # Creation uses the same unprivileged GTK page with actual sudo/useradd/passwd.
    # Only this disposable container receives a test sudoers policy.
    policy = Path("/etc/sudoers.d/rampi-ci")
    assert not policy.exists()
    original_shadow = Path("/etc/shadow").read_text().split("rampi:", 1)[1].splitlines()[0]
    script.write_text(
        prefix + "timeout 45 /build/target/debug/rampi-native --account-create-ui-check\n"
    )
    for mode in ["denied", "allowed"]:
        if mode == "allowed":
            # useradd may succeed while merely warning about a preexisting home.
            # Rampi must keep that account locked rather than adopt unsafe data.
            unsafe_home = Path("/home/rampi-unsafe")
            assert not unsafe_home.exists()
            unsafe_home.mkdir(mode=0o755)
            unsafe_home.joinpath("preserved").write_text("existing root data")
            Path("/home/rampi-symlink").symlink_to(unsafe_home, target_is_directory=True)
            policy.write_text("rampi ALL=(root) NOPASSWD: /usr/sbin/useradd, /usr/bin/passwd\n")
            policy.chmod(0o440)
            subprocess.run(["visudo", "-cf", "/etc/sudoers"], check=True, capture_output=True)
        result = subprocess.run(
            ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", str(script)],
            env={
                **os.environ,
                "LC_ALL": "C",
                "RAMPI_TEST_ACCOUNT_FILE": str(secrets),
                "RAMPI_TEST_CREATE_MODE": mode,
            },
            capture_output=True,
            text=True,
            timeout=55,
        )
        assert not any(value in result.stdout + result.stderr for value in [old, new, created])
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        marker = f"RAMPI_RUST_ACCOUNT_CREATE_{mode.upper()}_OK"
        assert marker in result.stdout
        print(result.stdout.strip())
        assert (
            original_shadow == Path("/etc/shadow").read_text().split("rampi:", 1)[1].splitlines()[0]
        )
        if mode == "denied":
            assert not any(
                row.split(":")[0] == "rampi-created"
                for row in Path("/etc/passwd").read_text().splitlines()
            )
    account = pwd.getpwnam("rampi-created")
    assert unsafe_home.stat().st_uid == 0 and unsafe_home.stat().st_mode & 0o777 == 0o755
    assert unsafe_home.joinpath("preserved").read_text() == "existing root data"
    assert Path("/home/rampi-symlink").is_symlink()
    for name in ["rampi-unsafe", "rampi-symlink"]:
        shadow = Path("/etc/shadow").read_text().split(name + ":", 1)[1].split(":", 1)[0]
        assert shadow.startswith("!"), "Unsafe account was assigned a usable password"
    home = Path(account.pw_dir)
    assert home.stat().st_uid == account.pw_uid and home.stat().st_mode & 0o777 == 0o700
    assert account.pw_uid >= 1000 and account.pw_shell == "/bin/bash"
    authentication = subprocess.run(
        ["pamtester", "rampi-ci", "rampi-created", "authenticate"],
        input=created + "\n",
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert authentication.returncode == 0, "New account cannot actually authenticate with PAM"
    assert "sudo" not in subprocess.check_output(["id", "-nG", "rampi-created"], text=True).split()
    policy.unlink()
print("RAMPI_RUST_ACCOUNT_PAM_OK")
print(
    "PASS: real unprivileged passwd, PAM old/wrong/new authentication and Linux file isolation; "
    "no graphical greetd login proof."
)
