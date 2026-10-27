"""Authenticate the stock first account after a second normal boot of the same image copy."""

import hashlib
import json
import os
import pwd
import runpy
import shutil
from pathlib import Path

CAPTURES = Path("/opt/rampi-captures")
STATE = Path("/opt/rampi-source/first-user-reboot-private.json")


def main():
    if os.geteuid() or not Path("/etc/rampi-image-acceptance-vm").is_file():
        raise RuntimeError("Only in the disposable installed-image guest")
    cmdline = Path("/proc/cmdline").read_text().split()
    if "rampi.image_acceptance=1" not in cmdline or any(
        value.startswith("systemd.unit=") for value in cmdline
    ):
        raise RuntimeError("Second boot must use the installed default target")
    os.umask(0o077)
    if STATE.is_symlink() or STATE.stat().st_uid or STATE.stat().st_mode & 0o077:
        raise RuntimeError("Unsafe disposable first-account state")
    state = json.loads(STATE.read_text())
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if boot_id == state["boot_id"]:
        raise RuntimeError("A second real kernel boot is required")
    account = pwd.getpwuid(1000)
    if account.pw_name != state["user"]:
        raise RuntimeError("First account changed between boots")
    api = runpy.run_path("/opt/rampi-source/scripts/virtual/test-login-guest.py")
    run = api["run"]
    if run("systemctl", "get-default").stdout.strip() != b"graphical.target":
        raise RuntimeError("Installed graphical boot target was not preserved")
    for unit in ("userconfig.service", "rampi-first-user.service"):
        if run("systemctl", "is-enabled", "--quiet", unit, check=False).returncode == 0:
            raise RuntimeError("Completed first-user setup was re-enabled")
    api["greeter_ready"]()
    # Remove the old UID receipt so that only the new authenticated session counts.
    receipt = Path(account.pw_dir, ".rampi-login-uid")
    receipt.unlink()
    api["login"](account.pw_name, state["password"])
    api["wait"](receipt.is_file, "first account PAM login after normal reboot")
    if receipt.read_text().strip() != "1000":
        raise RuntimeError("Wrong session UID after reboot")
    api["wait"](
        lambda: b"org.rampi.Workstation" in api["as_user"](
            account.pw_name, "wlrctl", "toplevel", "list", check=False,
        ).stdout,
        "mapped native workstation after normal reboot",
    )
    visible = runpy.run_path("/opt/rampi-source/scripts/check-login-evidence.py")[
        "visible_capture"
    ]
    screenshot = Path(account.pw_dir, ".rampi-first-user-reboot.png")

    def painted():
        api["as_user"](account.pw_name, "grim", str(screenshot))
        try:
            visible(screenshot)
            return True
        except ValueError:
            return False

    api["wait"](painted, "visible first-account workstation after reboot")
    api["native_keyring"](account.pw_name, "check", state["attribute"], state["secret"])
    shutil.copyfile(screenshot, CAPTURES / "first-user-reboot.png")
    (CAPTURES / "first-user-reboot.png").chmod(0o644)
    api["as_user"](account.pw_name, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
    api["greeter_ready"]()
    proof = {
        "normal_default_target_boot": True,
        "different_kernel_boot_id": True,
        "same_first_account": True,
        "uid": 1000,
        "pam_authenticated": True,
        "persisted_keyring_recovered": True,
        "native_surface_visible": True,
        "stock_wizard_remained_disabled": True,
        "binary_sha256": hashlib.sha256(
            Path("/opt/rampi/current/rampi-native").read_bytes()
        ).hexdigest(),
    }
    (CAPTURES / "first-user-reboot-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    (CAPTURES / "first-user-reboot-proof.json").chmod(0o644)
    STATE.unlink()
    print("RAMPI_FIRST_USER_NORMAL_REBOOT_PAM_OK", flush=True)


if __name__ == "__main__":
    main()
