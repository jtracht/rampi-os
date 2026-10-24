"""Installed-image claims must identify an actual successful Pi image boot."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "image_login", Path(__file__).resolve().parents[1] / "scripts/check-image-login-evidence.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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
