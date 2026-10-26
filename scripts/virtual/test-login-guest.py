"""Actual wlgreet, greetd, PAM and native user sessions in a designated QEMU VM."""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import runpy
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

SOURCE = Path("/opt/rampi-source")
CAPTURES = Path("/opt/rampi-captures")
DISPLAYS: dict[str, str] = {}


def run(*args, data=None, check=True):
    result = subprocess.run(args, input=data, capture_output=True, timeout=60)
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.decode(errors='replace')[-1500:]}")
    return result


def wait(predicate, description, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.3)
    raise RuntimeError("Timed out: " + description)


def as_user(user, *args, data=None, check=True):
    uid = pwd.getpwnam(user).pw_uid
    return run(
        "runuser",
        "-u",
        user,
        "--",
        "env",
        f"XDG_RUNTIME_DIR=/run/user/{uid}",
        f"WAYLAND_DISPLAY={DISPLAYS.get(user, 'wayland-0')}",
        f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
        *args,
        data=data,
        check=check,
    )


def greeter_ready():
    uid = pwd.getpwnam("_greetd").pw_uid
    runtime = Path(f"/run/user/{uid}")
    visible_capture = runpy.run_path(str(SOURCE / "scripts/check-login-evidence.py"))[
        "visible_capture"
    ]
    picture = runtime / "rampi-greeter-ready.png"

    def ready():
        # A socket pathname can predate the compositor accepting connections,
        # and a restarted session can select a different display number.
        sockets = [item for item in runtime.glob("wayland-*") if item.is_socket()]
        for item in sorted(sockets, key=lambda item: item.stat().st_mtime, reverse=True):
            DISPLAYS["_greetd"] = item.name
            try:
                if as_user("_greetd", "wlrctl", "toplevel", "list", check=False).returncode:
                    continue
                if as_user("_greetd", "grim", str(picture), check=False).returncode:
                    continue
                visible_capture(picture)
                return True
            except (ValueError, subprocess.TimeoutExpired):
                continue
        return False

    wait(ready, "reachable compositor with a visibly painted greeter")


def login(user, password):
    # Password reaches the existing virtual-keyboard tool on stdin, never argv.
    as_user("_greetd", "wtype", user, "-k", "Return")
    time.sleep(3)
    as_user("_greetd", "wtype", "-", "-k", "Return", data=password.encode())


def keyring_lookup(user, attribute):
    return as_user(
        user,
        "timeout",
        "15",
        "secret-tool",
        "lookup",
        "rampi-pam-acceptance",
        attribute,
        check=False,
    )


def native_keyring(user, mode, attribute, secret):
    request = {"mode": mode, "profile": "pam-acceptance-" + attribute, "token": secret}
    result = as_user(
        user,
        "/usr/local/bin/rampi",
        "--pam-keyring-check",
        data=json.dumps(request).encode(),
    )
    if (
        b"RAMPI_NATIVE_PAM_KEYRING_OK" not in result.stdout
        or b"RAMPI_NATIVE_PAM_STREAM_KEYRING_OK" not in result.stdout
    ):
        raise RuntimeError("Native Secret Service acceptance result missing")


def keyring_store(user, attribute, secret):
    # Exercise the real Secret Service. Never feed a keyring password or invoke
    # its unlock method: only the preceding greetd/PAM login may unlock it.
    # The production adapter must work before libsecret can create or select a
    # collection on its behalf. This prevents a generic CLI masking a Rampi bug.
    native_keyring(user, "store", attribute, secret)
    as_user(
        user,
        "timeout",
        "15",
        "secret-tool",
        "store",
        "--label=Rampi PAM acceptance",
        "rampi-pam-acceptance",
        attribute,
        data=secret.encode(),
    )
    result = keyring_lookup(user, attribute)
    if result.returncode or result.stdout.rstrip(b"\n") != secret.encode():
        raise RuntimeError("Personal Secret Service round trip failed after PAM login")
    keyrings = Path("/home", user, ".local/share/keyrings")
    encrypted = [item for item in keyrings.glob("*.keyring") if item.is_file()]
    if not encrypted or any(secret.encode() in item.read_bytes() for item in encrypted):
        raise RuntimeError("Encrypted personal keyring evidence missing")
    return keyrings


def install():
    run("bash", str(SOURCE / "installer/raspberrypi/keyring-profile.sh"), "--install")
    target = Path("/opt/rampi/login-test")
    target.mkdir(parents=True, exist_ok=True)
    next_binary = target / "rampi-native.next"
    shutil.copy2(SOURCE / "rampi-native", next_binary)
    next_binary.chmod(0o755)
    next_binary.replace(target / "rampi-native")
    assets = target / "assets"
    for name in ["branding", "icons", "sounds"]:
        shutil.copytree(SOURCE / "client/rampi" / name, assets / name, dirs_exist_ok=True)
    selected = Path("/opt/rampi/current")
    if selected.exists() and selected.resolve() != target:
        raise RuntimeError("Unexpected pre-existing installation in test VM")
    if not selected.exists():
        selected.symlink_to(target)
    Path("/opt/rampi").chmod(0o755)
    target.chmod(0o755)
    for item in target.rglob("*"):
        item.chmod(0o755 if item.is_dir() or item.name == "rampi-native" else 0o644)
    for name in ["rampi", "rampi-session", "rampi-wayland-start", "rampi-greeter"]:
        shutil.copy2(SOURCE / "system" / name, Path("/usr/local/bin") / name)
        Path("/usr/local/bin", name).chmod(0o755)
    Path("/etc/systemd/user").mkdir(exist_ok=True)
    shutil.copy2(SOURCE / "system/rampi.service", "/etc/systemd/user/rampi.service")
    Path("/etc/systemd/user/rampi.service").chmod(0o644)
    for name in ["greeter", "labwc"]:
        directory = Path("/etc/xdg/rampi") / name
        directory.mkdir(parents=True, exist_ok=True)
        config = "greeter.xml" if name == "greeter" else "rc.xml"
        shutil.copy2(SOURCE / "system/labwc" / config, directory / "rc.xml")
        Path("/etc/xdg/rampi").chmod(0o755)
        directory.chmod(0o755)
        (directory / "rc.xml").chmod(0o644)
    shutil.copy2(SOURCE / "system/wlgreet.toml", "/etc/xdg/rampi/greeter/wlgreet.toml")
    Path("/etc/xdg/rampi/greeter/wlgreet.toml").chmod(0o644)
    configure_test_session()


def configure_test_session():
    image_test = "--installed-image" in sys.argv
    backends = "headless" if image_test else "headless,libinput"
    wrapper = Path("/usr/local/bin/rampi-login-test-session")
    wrapper.write_text(
        "#!/bin/sh\nset -eu\numask 077\n"
        'id -u > "$HOME/.rampi-login-uid.tmp"\n'
        'mv "$HOME/.rampi-login-uid.tmp" "$HOME/.rampi-login-uid"\n'
        f"export WLR_BACKENDS={backends} WLR_RENDERER=pixman "
        "WLR_HEADLESS_OUTPUTS=1 LIBSEAT_BACKEND=logind\n"
        "exec /usr/local/bin/rampi-session\n"
    )
    wrapper.chmod(0o755)
    production = (
        Path("/etc/greetd/config.toml") if image_test else SOURCE / "system/greetd.toml"
    ).read_text()
    production = production.replace("/usr/local/bin/rampi-session", str(wrapper))
    if image_test:
        # Represent both designated input devices through existing Wayland
        # tools. wlgreet 0.5 requests wl_pointer even during keyboard-only input;
        # wlroots 0.20 rejects that unless a pointer capability has existed.
        helper = Path("/usr/local/bin/rampi-image-test-greeter")
        branded = "/usr/local/bin/rampi-greeter" in production
        greeter_program = "/usr/local/bin/rampi-greeter" if branded else "/usr/sbin/wlgreet"
        helper.write_text(
            "#!/bin/sh\nwtype -s 1500000 &\nkeyboard=$!\n"
            "trap 'kill \"$keyboard\" 2>/dev/null || true' EXIT\n"
            f'sleep 1\nwlrctl pointer move 0 0\n{greeter_program} "$@"\n'
        )
        helper.chmod(0o755)
        production = production.replace(greeter_program, str(helper))
    production = production.replace(
        'command = "',
        f'command = "env WLR_BACKENDS={backends} WLR_RENDERER=pixman '
        "WLR_HEADLESS_OUTPUTS=1 LIBSEAT_BACKEND=logind ",
        1,
    )
    if "--greeter-diagnostic" in sys.argv:
        production = production.replace(
            "env WLR_BACKENDS=", "env WAYLAND_DEBUG=server WLR_BACKENDS="
        )
        production = production.replace("/usr/bin/labwc ", "/usr/bin/labwc -d ")
    uid = pwd.getpwnam("_greetd").pw_uid
    production = production.replace("'\"", f"' >> /run/user/{uid}/rampi-greeter.log 2>&1\"")
    Path("/etc/greetd/config.toml").write_text(production)
    run("systemctl", "daemon-reload")
    run("systemctl", "reset-failed", "greetd")


def main():
    image_test = (
        "--installed-image" in sys.argv
        and Path("/etc/rampi-image-acceptance-vm").is_file()
        and "rampi.image_acceptance=1" in Path("/proc/cmdline").read_text()
    )
    if (
        not Path("/etc/rampi-acceptance-vm").is_file()
        or not image_test
        and run("systemd-detect-virt", "--vm", "--quiet", check=False).returncode
    ):
        raise SystemExit("Only inside the designated isolated QEMU guest")
    os.umask(0o077)
    # Provision test tools before boot. The installed-image guest has no
    # package-network dependency, and acceptance must not update its libraries.
    if shutil.which("wlrctl") is None:
        raise RuntimeError("Test guest was not provisioned with wlrctl")
    if image_test:
        # The image's actual installed program, assets, launchers and greeter
        # profile stay in place. Only fixture accounts and headless test input
        # are added to a disposable disk copy by the external validator.
        configure_test_session()
    else:
        install()
    users = ["rampi-login", "rampi-other"]
    reset_keyrings = "--debug-keyring-reset" in sys.argv
    if reset_keyrings and (
        image_test or Path("/etc/rampi-acceptance-vm").read_text().strip() != "isolated-qemu"
    ):
        raise RuntimeError("Fixture keyrings may only be reset in the resumed development guest")
    passwords = {}
    for user in users:
        try:
            pwd.getpwnam(user)
        except KeyError:
            run("useradd", "--create-home", "--shell", "/bin/bash", user)
        if reset_keyrings:
            home = Path("/home", user)
            keyrings = home / ".local/share/keyrings"
            if (
                home.is_symlink()
                or keyrings.is_symlink()
                or not keyrings.resolve().is_relative_to(home)
            ):
                raise RuntimeError("Unsafe fixture keyring path")
            if keyrings.exists():
                keyrings.rename(keyrings.with_name(f"keyrings-before-debug-{time.time_ns()}"))
            # Diagnostic proposal only: let PAM create/unlock the login keyring
            # before the session initializes Secret Service's exported objects.
            dropin = home / ".config/systemd/user/gnome-keyring-daemon.service.d"
            as_user(user, "mkdir", "-p", str(dropin))
            as_user(
                user,
                "tee",
                str(dropin / "50-rampi-debug-ordering.conf"),
                data=(
                    b"[Service]\nExecStart=\nExecStart=/usr/bin/gnome-keyring-daemon --foreground "
                    b"--components=pkcs11 --control-directory=%t/keyring\n"
                ),
            )
            as_user(user, "systemctl", "--user", "daemon-reload", check=False)
        Path("/home", user, ".rampi-login-uid").unlink(missing_ok=True)
        passwords[user] = secrets.token_urlsafe(24)
        run("chpasswd", data=f"{user}:{passwords[user]}\n".encode())
    run("systemctl", "restart", "greetd")
    greeter_ready()
    if "--greeter-diagnostic" in sys.argv:
        # No password or username input in protocol diagnostics. This mode is
        # intentionally insufficient for the normal acceptance checker.
        time.sleep(15)
        raise RuntimeError("Diagnostic-only greeter run; no authentication attempted")
    as_user("_greetd", "wtype", "-M", "ctrl", "-M", "alt", "-k", "Home", "-m", "alt", "-m", "ctrl")
    time.sleep(1)
    processes = run(
        "pgrep", "-u", str(pwd.getpwnam("_greetd").pw_uid), "-x", "rampi-native", check=False
    ).stdout.split()
    if len(processes) != 1:
        raise RuntimeError("Greeter requires exactly one branding-only process")
    for pid in processes:
        arguments = Path(f"/proc/{int(pid)}/cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        if arguments[1:] != [b"--login-background"]:
            raise RuntimeError("Greeter launched an unauthenticated workstation")
    greeter_png = f"/run/user/{pwd.getpwnam('_greetd').pw_uid}/rampi-greeter.png"
    visible_branding = runpy.run_path(str(SOURCE / "scripts/check-login-evidence.py"))[
        "visible_branding"
    ]

    def branding_ready():
        # wlgreet can paint before the independent GTK branding process maps its
        # first frame on a cold emulated Pi. Require actual readiness, not a delay.
        result = as_user("_greetd", "wlrctl", "toplevel", "list", check=False)
        (CAPTURES / "branding-surfaces.txt").write_bytes(result.stdout)
        (CAPTURES / "branding-surfaces.txt").chmod(0o644)
        if b"org.rampi.Workstation" in result.stdout:
            raise RuntimeError("Unauthenticated workstation exposed by greeter")
        if result.returncode or b"org.rampi.LoginBranding" not in result.stdout:
            return False
        if as_user("_greetd", "grim", greeter_png, check=False).returncode:
            return False
        shutil.copyfile(greeter_png, CAPTURES / "greeter.png")
        (CAPTURES / "greeter.png").chmod(0o644)
        try:
            visible_branding(CAPTURES / "greeter.png")
        except ValueError:
            return False
        return True

    wait(branding_ready, "mapped branding-only greeter with visible original logo")
    print("RAMPI_GRAPHICAL_LOGIN_NO_UNAUTH_UI_OK", flush=True)
    print("RAMPI_GRAPHICAL_LOGIN_BRANDING_OK", flush=True)
    failures = run("journalctl", "-b", "-u", "greetd", "--no-pager").stdout.count(
        b"authentication failure"
    )
    login(users[0], "incorrect-disposable-test-password")
    wait(
        lambda: (
            run("journalctl", "-b", "-u", "greetd", "--no-pager").stdout.count(
                b"authentication failure"
            )
            > failures
        ),
        "actual PAM authentication rejection",
        seconds=30,
    )
    if Path("/home", users[0], ".rampi-login-uid").exists():
        raise RuntimeError("PAM accepted an incorrect password")
    print("RAMPI_GRAPHICAL_LOGIN_REJECT_OK", flush=True)
    run("systemctl", "restart", "greetd")
    greeter_ready()
    evidence = []
    keyring_attribute = secrets.token_hex(16)
    keyring_values = {user: secrets.token_urlsafe(32) for user in users}
    for user in users:
        login(user, passwords[user])
        proof = Path("/home", user, ".rampi-login-uid")
        wait(proof.is_file, "authenticated session UID")
        uid = pwd.getpwnam(user).pw_uid
        observed_uid = proof.read_text().strip()
        if observed_uid != str(uid):
            raise RuntimeError(
                f"Incorrect authenticated session identity: expected {uid}, got {observed_uid!r}"
            )
        wait(
            lambda user=user: (
                as_user(
                    user,
                    "systemctl",
                    "--user",
                    "is-active",
                    "--quiet",
                    "rampi.service",
                    check=False,
                ).returncode
                == 0
            ),
            "actual native user service",
        )
        wait(
            lambda uid=uid: (
                run("pgrep", "-u", str(uid), "-x", "rampi-native", check=False).returncode == 0
            ),
            "actual native application process",
        )
        wait(
            lambda user=user: (
                b"org.rampi.Workstation"
                in as_user(user, "wlrctl", "toplevel", "list", check=False).stdout
            ),
            "mapped native application surface",
        )
        screenshot = f"/home/{user}/.rampi-login.png"
        visible_capture = runpy.run_path(str(SOURCE / "scripts/check-login-evidence.py"))[
            "visible_capture"
        ]

        def painted(user=user, screenshot=screenshot, visible_capture=visible_capture):
            as_user(user, "grim", screenshot)
            try:
                visible_capture(Path(screenshot))
                return True
            except ValueError:
                return False

        wait(painted, "actual visible native application frame")
        shutil.copyfile(screenshot, CAPTURES / f"{user}.png")
        (CAPTURES / f"{user}.png").chmod(0o644)
        personal = Path("/home") / user / ".config/rampi"
        if personal.stat().st_mode & 0o777 != 0o700 or personal.stat().st_uid != uid:
            raise RuntimeError("Native personal configuration permissions are not private")
        other = users[1] if user == users[0] else users[0]
        pid = int(
            as_user(
                user,
                "systemctl",
                "--user",
                "show",
                "rampi.service",
                "--property=MainPID",
                "--value",
            ).stdout
        )
        process_env = dict(
            item.split(b"=", 1)
            for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
            if b"=" in item
        )
        if (
            process_env.get(b"DBUS_SESSION_BUS_ADDRESS")
            != f"unix:path=/run/user/{uid}/bus".encode()
        ):
            raise RuntimeError("Native application did not reuse the existing personal session bus")
        absent = keyring_lookup(user, keyring_attribute)
        if absent.returncode != 1 or absent.stdout:
            raise RuntimeError("Another user's personal secret appeared in this session")
        keyrings = keyring_store(user, keyring_attribute, keyring_values[user])
        for item in keyrings.glob("*.keyring"):
            if as_user(other, "cat", str(item), check=False).returncode == 0:
                raise RuntimeError("Another account read an encrypted keyring file")
        agent_socket = process_env.get(b"SSH_AUTH_SOCK", b"").decode()
        if not agent_socket:
            raise RuntimeError("Native systemd service did not inherit its SSH agent")

        def agent_status(account=user, socket=agent_socket):
            return as_user(
                account, "env", f"SSH_AUTH_SOCK={socket}", "/usr/bin/ssh-add", "-l", check=False
            ).returncode

        if agent_status() != 1 or agent_status(other) != 2:
            raise RuntimeError("Empty personal SSH agent unavailable or accessible by another user")
        if as_user(other, "cat", str(proof), check=False).returncode == 0:
            raise RuntimeError("Another account read the private login proof")
        evidence.append(
            {
                "user": user,
                "uid": uid,
                "session_uid": int(proof.read_text()),
                "native_process": True,
                "binary_sha256": hashlib.sha256(
                    Path("/opt/rampi/current/rampi-native").read_bytes()
                ).hexdigest(),
                "config_mode": oct(personal.stat().st_mode & 0o777),
                "config_uid": personal.stat().st_uid,
                "ssh_agent_private": True,
                "pam_keyring_roundtrip_private": True,
                "personal_bus_reused": True,
            }
        )
        as_user(user, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
        wait(
            lambda uid=uid: (
                run("pgrep", "-u", str(uid), "-x", "rampi-native", check=False).returncode != 0
            ),
            "native application termination on logout",
        )
        greeter_ready()
        wait(
            lambda status=agent_status: status() == 2,
            "session-owned SSH agent termination",
            seconds=20,
        )
    # Both accounts must recover their own persisted encrypted secret through
    # another real PAM login and a new daemon, without a manual unlock.
    for account in evidence:
        user, uid = account["user"], account["uid"]
        wait(
            lambda uid=uid: (
                run(
                    "pgrep", "-u", str(uid), "-f", "(^|/)gnome-keyring-daemon( |$)", check=False
                ).returncode
                != 0
            ),
            "personal keyring daemon termination after logout",
            seconds=30,
        )
        login(user, passwords[user])
        wait(
            lambda user=user: (
                b"org.rampi.Workstation"
                in as_user(user, "wlrctl", "toplevel", "list", check=False).stdout
            ),
            "mapped native session after keyring relogin",
        )
        recovered = keyring_lookup(user, keyring_attribute)
        if recovered.returncode or recovered.stdout.rstrip(b"\n") != keyring_values[user].encode():
            raise RuntimeError("PAM relogin did not unlock the persisted personal keyring")
        native_keyring(user, "check", keyring_attribute, keyring_values[user])
        as_user(user, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
        greeter_ready()
        account["pam_keyring_relogin"] = True
    print("RAMPI_GRAPHICAL_LOGIN_PAM_KEYRING_PRIVATE_OK", flush=True)
    print("RAMPI_GRAPHICAL_LOGIN_PAM_KEYRING_RELOGIN_OK", flush=True)
    print("RAMPI_GRAPHICAL_LOGIN_PAM_STREAM_KEYRING_OK", flush=True)
    if (
        run("pgrep", "-x", "Xorg", check=False).returncode == 0
        or run("pgrep", "-x", "Xwayland", check=False).returncode == 0
    ):
        raise RuntimeError("Login launched an X11 server")
    (CAPTURES / "login-proof.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (CAPTURES / "login-proof.json").chmod(0o644)
    print("RAMPI_GRAPHICAL_LOGIN_TWO_USERS_OK", flush=True)
    print("RAMPI_GRAPHICAL_LOGIN_SSH_AGENT_OK", flush=True)
    print("RAMPI_GRAPHICAL_LOGIN_OK", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        uid = pwd.getpwnam("_greetd").pw_uid
        log = Path(f"/run/user/{uid}/rampi-greeter.log")
        if log.is_file():
            print(log.read_text(errors="replace")[-6000:], flush=True)
            if "--greeter-diagnostic" in sys.argv:
                shutil.copyfile(log, CAPTURES / "greeter-diagnostic.log")
                (CAPTURES / "greeter-diagnostic.log").chmod(0o644)
        diagnostic = run("journalctl", "-b", "-u", "greetd", "--no-pager", "-n", "30", check=False)
        print(diagnostic.stdout.decode(errors="replace"), flush=True)
        diagnostic = run(
            "journalctl",
            "-b",
            "--no-pager",
            "-n",
            "30",
            "_SYSTEMD_USER_UNIT=rampi.service",
            check=False,
        )
        print(diagnostic.stdout.decode(errors="replace"), flush=True)
        raise
