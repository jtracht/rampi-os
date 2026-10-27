"""Require actual installed-image graphical login with unchanged program files."""

import argparse
import json
import re
import runpy
from pathlib import Path


def check_metadata(environment, expected_source=None, expected_image=None):
    if environment.get("installed_pi_image") is not True or environment.get("machine") != "raspi3b":
        raise ValueError("Not an installed Pi image boot")
    if (
        type(environment.get("guest_exit_code")) is not int
        or environment["guest_exit_code"] != 0
        or environment.get("stopped_after_synced_guest_result") is not True
    ):
        raise ValueError("Image guest did not finish and sync its results successfully")
    for key, length, expected in [
        ("image_source_revision", 40, expected_source),
        ("original_compressed_image_sha256", 64, expected_image),
    ]:
        value = environment.get(key, "")
        if (
            not re.fullmatch(r"[a-f0-9]{" + str(length) + r"}", value)
            or expected
            and expected != value
        ):
            raise ValueError("Image provenance mismatch: " + key)
    if environment.get("architecture") != "arm64":
        raise ValueError("Pi image must contain ARM64 userspace")


def check_first_user(first, binary_sha256):
    for key in (
        "pristine_locked_account",
        "stock_interactive_userconf",
        "graphical_login_after_userconf",
        "wizard_password_authenticated_by_pam",
        "pam_keyring_relogin",
        "kernel_enter_press_release_observed",
        "native_surface_visible",
        "stock_wizard_disabled",
        "completion_service_disabled",
    ):
        if first.get(key) is not True:
            raise ValueError("Missing pristine first-user acceptance: " + key)
    if (
        first.get("credentials_preconfigured") is not False
        or first.get("uid") != 1000
        or first.get("session_uid") != 1000
        or first.get("default_target") != "graphical.target"
        or first.get("input") != "linux-kernel-uinput-ydotool"
        or first.get("usb_keyboard_transport_tested") is not False
        or first.get("binary_sha256") != binary_sha256
    ):
        raise ValueError("First-user evidence does not match the installed workstation")
    if not first.get("input_tool_package_version", "").startswith("1.0."):
        raise ValueError("Actual existing kernel input tool version is missing")


def check_kernel_keys(log):
    keys = re.findall(r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]*\), value ([012])", log)
    if {("28", "0"), ("28", "1")} - set(keys) or any(code != "28" for code, _ in keys):
        raise ValueError("Require actual Enter press/release without any credential key recording")


def check(directory, expected_source=None, expected_image=None):
    environment = json.loads((directory / "environment.json").read_text(encoding="utf-8"))
    check_metadata(environment, expected_source, expected_image)
    runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))["check"](
        directory, environment["native_binary_sha256"]
    )
    log = (directory / "serial.log").read_text(encoding="utf-8", errors="replace")
    if "RAMPI_INSTALLED_FILES_UNCHANGED_OK" not in log:
        raise ValueError("Installed workstation file preservation was not verified")
    if "RAMPI_PRISTINE_FIRST_USER_PAM_OK" not in log:
        raise ValueError("Actual stock first-user wizard and PAM login were not verified")
    first = json.loads((directory / "captures/first-user-proof.json").read_text(encoding="utf-8"))
    check_first_user(first, environment["native_binary_sha256"])
    check_kernel_keys((directory / "captures/first-user-precredential-input.log").read_text(
        encoding="utf-8", errors="replace"
    ))
    runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))["visible_capture"](
        directory / "captures/first-user.png"
    )
    return environment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-source")
    parser.add_argument("--expected-image-sha256")
    options = parser.parse_args()
    check(options.directory, options.expected_source, options.expected_image_sha256)
    print("PASS: installed Pi image GUI, PAM, private profiles and unchanged workstation files.")
