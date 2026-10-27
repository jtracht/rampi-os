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


def check_first_user(first, binary_sha256, *, preconfigured=False):
    for key in (
        "graphical_login_after_userconf",
        "pam_keyring_relogin",
        "native_surface_visible",
        "stock_wizard_disabled",
        "completion_service_disabled",
    ):
        if first.get(key) is not True:
            raise ValueError("Missing pristine first-user acceptance: " + key)
    credential_proof = ("configured_password_authenticated_by_pam" if preconfigured
                        else "wizard_password_authenticated_by_pam")
    if first.get(credential_proof) is not True:
        raise ValueError("The configured first-account credential was not authenticated by PAM")
    if (
        first.get("credentials_preconfigured") is not preconfigured
        or first.get("pristine_locked_account") is not (not preconfigured)
        or first.get("stock_interactive_userconf") is not (not preconfigured)
        or first.get("kernel_enter_press_release_observed") is not (not preconfigured)
        or first.get("uid") != 1000
        or first.get("session_uid") != 1000
        or first.get("default_target") != "graphical.target"
        or first.get("input") != (
            "official-userconf-boot-file" if preconfigured else "linux-kernel-uinput-ydotool"
        )
        or first.get("usb_keyboard_transport_tested") is not False
        or first.get("binary_sha256") != binary_sha256
    ):
        raise ValueError("First-user evidence does not match the installed workstation")
    if preconfigured and first.get("boot_configuration_consumed") is not True:
        raise ValueError("The stock service did not consume its supported account boot file")
    if not first.get("input_tool_package_version", "").startswith("1.0."):
        raise ValueError("Actual existing kernel input tool version is missing")


def check_kernel_keys(log):
    keys = re.findall(r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]*\), value ([012])", log)
    if {("28", "0"), ("28", "1")} - set(keys) or any(code != "28" for code, _ in keys):
        raise ValueError("Require actual Enter press/release without any credential key recording")


def check_reboot(proof, binary_sha256):
    for key in (
        "normal_default_target_boot", "different_kernel_boot_id", "same_first_account",
        "pam_authenticated", "persisted_keyring_recovered", "native_surface_visible",
        "stock_wizard_remained_disabled",
    ):
        if proof.get(key) is not True:
            raise ValueError("Missing normal first-account reboot acceptance: " + key)
    if proof.get("uid") != 1000 or proof.get("binary_sha256") != binary_sha256:
        raise ValueError("Reboot evidence used another account or native program")


def check(directory, expected_source=None, expected_image=None, *, preconfigured=False):
    environment = json.loads((directory / "environment.json").read_text(encoding="utf-8"))
    check_metadata(environment, expected_source, expected_image)
    if environment.get("account_mode") != ("preconfigured" if preconfigured else "interactive"):
        raise ValueError("Image account provisioning mode mismatch")
    if environment.get("pristine_image_account_locked") is not True:
        raise ValueError("The original image account must be locked before test preparation")
    if preconfigured:
        for key, value in {
            "memory_mib": 1024, "cpus": 4, "physical_devices": False,
            "prepared_development_cache": False, "resumed_development_guest": False,
        }.items():
            if type(environment.get(key)) is not type(value) or environment[key] != value:
                raise ValueError("Invalid preconfigured image environment: " + key)
    else:
        runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))["check"](
            directory, environment["native_binary_sha256"]
        )
    log = (directory / "serial.log").read_text(encoding="utf-8", errors="replace")
    if "RAMPI_INSTALLED_FILES_UNCHANGED_OK" not in log:
        raise ValueError("Installed workstation file preservation was not verified")
    marker = ("RAMPI_PRECONFIGURED_FIRST_USER_PAM_OK" if preconfigured
              else "RAMPI_PRISTINE_FIRST_USER_PAM_OK")
    if marker not in log:
        raise ValueError("Actual stock first-user wizard and PAM login were not verified")
    first = json.loads((directory / "captures/first-user-proof.json").read_text(encoding="utf-8"))
    check_first_user(first, environment["native_binary_sha256"], preconfigured=preconfigured)
    if (environment.get("kernel_boots") != 2
            or "RAMPI_FIRST_USER_NORMAL_REBOOT_PAM_OK" not in log):
        raise ValueError("Two actual kernel boots and a normal first-account login are required")
    reboot = json.loads((directory / "captures/first-user-reboot-proof.json").read_text(
        encoding="utf-8",
    ))
    check_reboot(reboot, environment["native_binary_sha256"])
    if not preconfigured:
        check_kernel_keys((directory / "captures/first-user-precredential-input.log").read_text(
            encoding="utf-8", errors="replace"
        ))
    runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))["visible_capture"](
        directory / "captures/first-user.png"
    )
    runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))["visible_capture"](
        directory / "captures/first-user-reboot.png"
    )
    if not preconfigured:
        provisioned = check(
            directory / "preconfigured", environment["image_source_revision"],
            environment["original_compressed_image_sha256"], preconfigured=True,
        )
        if provisioned["native_binary_sha256"] != environment["native_binary_sha256"]:
            raise ValueError("The two first-account paths executed different programs")
    return environment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-source")
    parser.add_argument("--expected-image-sha256")
    parser.add_argument("--preconfigured", action="store_true")
    options = parser.parse_args()
    check(options.directory, options.expected_source, options.expected_image_sha256,
          preconfigured=options.preconfigured)
    print("PASS: installed Pi image GUI, PAM, private profiles and unchanged workstation files.")
