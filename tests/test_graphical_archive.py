"""Archive guards only: tiny fixture files never count as a graphical login."""

import io
import runpy
import tarfile
from pathlib import Path

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check-graphical-archive.py"))
NAMES = ["graphical-login/" + name for name in MODULE["FILES"]]


def archive(tmp_path, names, symlink=None):
    path = tmp_path / "evidence.tar.xz"
    with tarfile.open(path, "w:xz") as output:
        for name in names:
            item = tarfile.TarInfo(name)
            if name == symlink:
                item.type = tarfile.SYMTYPE
                item.linkname = "/outside-the-evidence-root"
                output.addfile(item)
            else:
                content = b"Not real login or image evidence"
                item.size = len(content)
                output.addfile(item, io.BytesIO(content))
    return path


@pytest.mark.parametrize("missing", [
    "first-user-proof.json", "first-user.png",
    "first-user-reboot-proof.json", "first-user-reboot.png",
])
def test_pristine_first_user_files_cannot_be_omitted(tmp_path, missing):
    path = archive(tmp_path, [name for name in NAMES if not name.endswith(missing)])
    with pytest.raises(ValueError):
        MODULE["read_members"](path)


def test_old_six_file_bundle_cannot_pass(tmp_path):
    path = archive(tmp_path, [name for name in NAMES if "/first-user" not in name])
    with pytest.raises(ValueError):
        MODULE["read_members"](path)


def test_boot_file_account_bundle_cannot_be_omitted(tmp_path):
    path = archive(tmp_path, [name for name in NAMES if "/preconfigured/" not in name])
    with pytest.raises(ValueError):
        MODULE["read_members"](path)


@pytest.mark.parametrize("extra", ["graphical-login/private-key", NAMES[0]])
def test_private_or_duplicate_file_rejected(tmp_path, extra):
    with pytest.raises(ValueError):
        MODULE["read_members"](archive(tmp_path, [*NAMES, extra]))


def test_symlink_is_not_image_proof(tmp_path):
    with pytest.raises(ValueError):
        MODULE["read_members"](archive(tmp_path, NAMES, symlink=NAMES[-1]))


def test_valid_archive_structure_is_not_login_acceptance(tmp_path):
    path = archive(tmp_path, NAMES)
    assert set(MODULE["read_members"](path)) == set(NAMES)
    with pytest.raises(ValueError):
        MODULE["check"](path, "a" * 40, "b" * 64, "c" * 64)
