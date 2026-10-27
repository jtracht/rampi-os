"""Installed-image claims must identify an actual successful Pi image boot."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "image_login", Path(__file__).resolve().parents[1] / "scripts/check-image-login-evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_kernel_input_receipt_requires_press_and_release():
    down = "Event: time 1, type 1 (EV_KEY), code 28 (KEY_ENTER), value 1\n"
    up = "Event: time 2, type 1 (EV_KEY), code 28 (KEY_ENTER), value 0\n"
    MODULE.check_kernel_keys(down + up)
    with pytest.raises(ValueError):
        MODULE.check_kernel_keys(down)
    with pytest.raises(ValueError):
        MODULE.check_kernel_keys("Event code 28 (KEY_ENTER)\n")
    with pytest.raises(ValueError):
        MODULE.check_kernel_keys(
            down + up + "Event: time 3, type 1 (EV_KEY), code 30 (KEY_A), value 1\n"
        )


def metadata():
    return dict(
        installed_pi_image=True,
        machine="raspi3b",
        guest_exit_code=0,
        stopped_after_synced_guest_result=True,
        architecture="arm64",
        image_source_revision="a" * 40,
        original_compressed_image_sha256="b" * 64,
    )


def test_valid_source_bound_image():
    MODULE.check_metadata(metadata(), "a" * 40, "b" * 64)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("installed_pi_image", False),
        ("machine", "virt"),
        ("guest_exit_code", 1),
        ("stopped_after_synced_guest_result", False),
        ("architecture", "amd64"),
        ("image_source_revision", "wrong"),
        ("original_compressed_image_sha256", "stale"),
    ],
)
def test_reject_other_or_failed_image(key, value):
    data = metadata()
    data[key] = value
    with pytest.raises(ValueError):
        MODULE.check_metadata(data)


def test_reject_different_producer():
    with pytest.raises(ValueError, match="provenance"):
        MODULE.check_metadata(metadata(), "c" * 40)


@pytest.mark.parametrize("omitted", [
    "normal_default_target_boot", "different_kernel_boot_id", "same_first_account",
    "pam_authenticated", "persisted_keyring_recovered", "native_surface_visible",
    "stock_wizard_remained_disabled", "uid", "binary_sha256",
])
def test_reboot_requires_real_account_and_persistence_evidence(omitted):
    proof = dict.fromkeys([
        "normal_default_target_boot", "different_kernel_boot_id", "same_first_account",
        "pam_authenticated", "persisted_keyring_recovered", "native_surface_visible",
        "stock_wizard_remained_disabled",
    ], True)
    proof.update(uid=1000, binary_sha256="d" * 64)
    MODULE.check_reboot(proof, "d" * 64)
    del proof[omitted]
    with pytest.raises(ValueError):
        MODULE.check_reboot(proof, "d" * 64)


def first_user():
    return {
        "pristine_locked_account": True,
        "stock_interactive_userconf": True,
        "credentials_preconfigured": False,
        "graphical_login_after_userconf": True,
        "wizard_password_authenticated_by_pam": True,
        "pam_keyring_relogin": True,
        "native_surface_visible": True,
        "uid": 1000,
        "session_uid": 1000,
        "stock_wizard_disabled": True,
        "completion_service_disabled": True,
        "default_target": "graphical.target",
        "input": "linux-kernel-uinput-ydotool",
        "kernel_enter_press_release_observed": True,
        "usb_keyboard_transport_tested": False,
        "input_tool_package_version": "1.0.4-2~bpo13+1",
        "binary_sha256": "d" * 64,
    }


def test_first_user_proof_matches_installed_binary():
    MODULE.check_first_user(first_user(), "d" * 64)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("pristine_locked_account", False),
        ("stock_interactive_userconf", False),
        ("credentials_preconfigured", True),
        ("graphical_login_after_userconf", False),
        ("wizard_password_authenticated_by_pam", False),
        ("pam_keyring_relogin", False),
        ("kernel_enter_press_release_observed", False),
        ("usb_keyboard_transport_tested", True),
        ("native_surface_visible", False),
        ("uid", 1001),
        ("session_uid", 0),
        ("stock_wizard_disabled", False),
        ("completion_service_disabled", False),
        ("default_target", "multi-user.target"),
        ("input", "preconfigured-account"),
        ("binary_sha256", "e" * 64),
    ],
)
def test_seeded_or_incomplete_first_user_proof_cannot_pass(key, value):
    proof = first_user()
    proof[key] = value
    with pytest.raises(ValueError):
        MODULE.check_first_user(proof, "d" * 64)


def test_existing_two_preseeded_users_do_not_prove_pristine_setup():
    with pytest.raises(ValueError):
        MODULE.check_first_user({}, "d" * 64)
