"""Observe stock userconf and authenticate its first account in the disposable image.

No account creation, password reset, replacement wizard or PAM bypass is allowed
here. Keyboard input comes from the host through QEMU's existing QMP API.
"""

import atexit
import hashlib
import json
import os
import pwd
import runpy
import secrets
import subprocess
import time
from pathlib import Path

CAPTURES = Path("/opt/rampi-captures")
CREDENTIALS = Path("/opt/rampi-source/first-user-credentials.json")


def command(*args):
    return subprocess.run(args, capture_output=True, timeout=15)


def active(unit):
    return command("systemctl", "is-active", "--quiet", unit).returncode == 0


def enabled(unit):
    return command("systemctl", "is-enabled", "--quiet", unit).returncode == 0


def monitor_precredential_keyboard():
    """Existing evtest observes only the designated emulated keyboard, without grab."""
    devices = [
        item for item in Path("/sys/class/input").glob("event*/device/name")
        if item.read_text().strip() == "QEMU QEMU USB Keyboard"
    ]
    if len(devices) != 1:
        raise RuntimeError("Exactly one emulated USB keyboard is required")
    destination = CAPTURES / "first-user-precredential-input.log"
    stream = destination.open("wb")
    device = "/dev/input/" + devices[0].parents[1].name
    process = subprocess.Popen(
        ["stdbuf", "-oL", "evtest", device], stdout=stream, stderr=subprocess.STDOUT
    )

    def stop():
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        stream.close()
        destination.chmod(0o644)

    atexit.register(stop)
    # Opening a process is not proof that its input descriptor is ready. Do
    # not permit the host's first key before evtest is actually listening.
    deadline = time.monotonic() + 15
    while "Testing ... (interrupt to exit)" not in destination.read_text(errors="replace"):
        if process.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError("Precredential input observer did not become ready")
        time.sleep(0.1)
    return stop


def main():
    if os.geteuid() or not Path("/etc/rampi-image-acceptance-vm").is_file():
        raise RuntimeError("Only in the disposable installed-image guest")
    os.umask(0o077)
    if command("systemctl", "get-default").stdout.strip() != b"multi-user.target":
        raise RuntimeError("Pristine image did not boot into stock first-user setup")
    if not enabled("userconfig.service") or not enabled("rampi-first-user.service"):
        raise RuntimeError("First-user services were not installed and enabled")
    original = pwd.getpwuid(1000)
    state = command("passwd", "-S", original.pw_name).stdout.split()
    if len(state) < 2 or state[1] != b"L" or active("greetd.service"):
        raise RuntimeError("Fixture accounts or a premature graphical login invalidate this test")
    credentials = json.loads(CREDENTIALS.read_text())
    api = runpy.run_path("/opt/rampi-source/scripts/virtual/test-login-guest.py")
    # Use the same headless rendering/test-input adaptation as the image's
    # existing graphical test. Do not start greetd or alter stock userconf.
    api["configure_test_session"]()
    Path("/run/rampi-image-test-session-configured").touch()
    stop_keyboard_monitor = monitor_precredential_keyboard()
    started = time.monotonic()
    seen = set()
    keyboard_seen = set()
    keyboard_questions = 0
    keyboard_sent_at = None
    precredential_diagnostic_saved = False
    while time.monotonic() - started < 480:
        # Read screen characters only to identify known stock dialogs. Never
        # export the console buffer: it may contain personal input.
        try:
            screen = Path("/dev/vcs8").read_bytes().decode("latin1")
        except OSError:
            screen = ""
        phase = None
        for marker, candidate in [
            ("Please enter new username:", "username"),
            ("Please set a password for", "password"),
            ("Please confirm the password:", "confirmation"),
        ]:
            if marker in screen:
                phase = candidate
                break
        if phase and phase not in seen:
            # Finish the non-grabbing diagnostic before the host is allowed to
            # send any username/password. No credential key event is recorded.
            stop_keyboard_monitor()
            seen.add(phase)
            print("RAMPI_FIRST_USER_INPUT=" + phase, flush=True)
        elif phase is None:
            keyboard_marker = next(
                (
                    marker
                    for marker in [
                        "Keyboard model:",
                        "Country of origin for the keyboard:",
                        "Keyboard layout:",
                        "Key to function as AltGr:",
                        "Compose key:",
                        "Alt+Backspace",
                        "Tastaturmodell:",
                        "Herkunftsland",
                        "Tastaturbelegung:",
                        "Taste, die als AltGr fungieren soll:",
                        "Compose-Taste:",
                    ]
                    if marker in screen
                ),
                None,
            )
            if keyboard_marker and keyboard_marker not in keyboard_seen:
                keyboard_seen.add(keyboard_marker)
                keyboard_questions += 1
                if keyboard_questions > 8:
                    raise RuntimeError("Unexpected stock keyboard configuration loop")
                print(f"RAMPI_FIRST_USER_INPUT=keyboard-{keyboard_questions}", flush=True)
                keyboard_sent_at = time.monotonic()
                time.sleep(1)
        # This snapshot is permitted only before the host has received any
        # username/password input request. Never export later console contents.
        if (
            not seen
            and keyboard_sent_at is not None
            and time.monotonic() - keyboard_sent_at > 8
            and not precredential_diagnostic_saved
        ):
            diagnostic = {
                "before_credential_input": True,
                "keyboard_questions": keyboard_questions,
                "matched_prompts": sorted(keyboard_seen),
                "active_vt": command("fgconsole").stdout.decode(errors="replace").strip(),
                "console_before_credentials": screen,
                "process_names": command("ps", "-eo", "comm=").stdout.decode(errors="replace"),
            }
            destination = CAPTURES / "first-user-precredential.json"
            destination.write_text(json.dumps(diagnostic, indent=2) + "\n")
            destination.chmod(0o644)
            precredential_diagnostic_saved = True
        if active("greetd.service"):
            if not {"username", "password", "confirmation"}.issubset(seen):
                raise RuntimeError("Graphical login appeared before stock account creation")
            break
        time.sleep(0.3)
    else:
        raise RuntimeError("Stock first-user setup did not reach graphical login")
    account = pwd.getpwuid(1000)
    state = command("passwd", "-S", account.pw_name).stdout.split()
    if (
        account.pw_name != credentials["user"]
        or state[1] != b"P"
        or enabled("userconfig.service")
        or enabled("rampi-first-user.service")
        or not enabled("greetd.service")
        or command("systemctl", "get-default").stdout.strip() != b"graphical.target"
    ):
        raise RuntimeError("Stock setup did not produce the expected usable account and boot state")
    api["greeter_ready"]()
    api["login"](account.pw_name, credentials["password"])
    proof = Path(account.pw_dir, ".rampi-login-uid")
    api["wait"](proof.is_file, "first account's actual PAM login")
    if proof.read_text().strip() != "1000":
        raise RuntimeError("First account session has the wrong UID")
    api["wait"](
        lambda: (
            b"org.rampi.Workstation"
            in api["as_user"](account.pw_name, "wlrctl", "toplevel", "list", check=False).stdout
        ),
        "first account's mapped native workstation",
    )
    screenshot = str(Path(account.pw_dir, ".rampi-first-user.png"))
    visible = runpy.run_path("/opt/rampi-source/scripts/check-login-evidence.py")["visible_capture"]

    def painted():
        api["as_user"](account.pw_name, "grim", screenshot)
        try:
            visible(Path(screenshot))
            return True
        except ValueError:
            return False

    api["wait"](painted, "visibly painted first-account workstation")
    import shutil

    shutil.copyfile(screenshot, CAPTURES / "first-user.png")
    (CAPTURES / "first-user.png").chmod(0o644)
    # The stock first account existed before /etc/skel was installed. Require
    # its real Secret Service as well as those of the later fixture accounts.
    attribute, secret = secrets.token_hex(16), secrets.token_urlsafe(32)
    api["keyring_store"](account.pw_name, attribute, secret)
    api["as_user"](account.pw_name, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
    api["greeter_ready"]()
    api["wait"](
        lambda: command(
            "pgrep", "-u", "1000", "-f", "(^|/)gnome-keyring-daemon( |$)"
        ).returncode != 0,
        "first account's keyring daemon termination", seconds=30,
    )
    api["login"](account.pw_name, credentials["password"])
    api["wait"](
        lambda: b"org.rampi.Workstation" in api["as_user"](
            account.pw_name, "wlrctl", "toplevel", "list", check=False
        ).stdout,
        "first account's actual session after another PAM login",
    )
    api["native_keyring"](account.pw_name, "check", attribute, secret)
    api["as_user"](account.pw_name, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
    api["greeter_ready"]()
    CREDENTIALS.unlink()
    evidence = {
        "pristine_locked_account": True,
        "stock_interactive_userconf": True,
        "credentials_preconfigured": False,
        "graphical_login_after_userconf": True,
        "wizard_password_authenticated_by_pam": True,
        "pam_keyring_relogin": True,
        "native_surface_visible": True,
        "uid": 1000,
        "session_uid": int(proof.read_text()),
        "stock_wizard_disabled": True,
        "completion_service_disabled": True,
        "default_target": "graphical.target",
        "input": "qemu-qmp-usb-keyboard",
        "binary_sha256": hashlib.sha256(
            Path("/opt/rampi/current/rampi-native").read_bytes()
        ).hexdigest(),
    }
    (CAPTURES / "first-user-proof.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (CAPTURES / "first-user-proof.json").chmod(0o644)
    print("RAMPI_PRISTINE_FIRST_USER_PAM_OK", flush=True)


if __name__ == "__main__":
    main()
