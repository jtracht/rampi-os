"""Package-selection preservation, not an image runtime acceptance test."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "image_profile", Path(__file__).resolve().parents[1] / "scripts/prepare-image-profile.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def package_file(tmp_path, contents):
    path = tmp_path / "stage2/01-sys-tweaks/00-packages"
    path.parent.mkdir(parents=True)
    path.write_text(contents)
    return path


def test_only_unused_cloud_service_is_omitted(tmp_path):
    before = "ssh less\nbluez bluez-firmware\nrpi-connect-lite\nrpifwcrypto\n"
    path = package_file(tmp_path, before)
    path.chmod(0o644)
    mode = path.stat().st_mode
    MODULE.configure(tmp_path)
    assert path.read_text() == "ssh less\nbluez bluez-firmware\nrpifwcrypto\n"
    assert path.stat().st_mode == mode


@pytest.mark.parametrize("contents", ["ssh\n", "rpi-connect-lite\nrpi-connect-lite\n"])
def test_changed_upstream_selection_is_preserved_and_rejected(tmp_path, contents):
    path = package_file(tmp_path, contents)
    with pytest.raises(ValueError, match="selection changed"):
        MODULE.configure(tmp_path)
    assert path.read_text() == contents


def test_missing_package_list_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="regular pinned"):
        MODULE.configure(tmp_path)
