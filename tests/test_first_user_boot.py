"""Stock boot-file preparation guards; these are not account/PAM acceptance."""

import json
import runpy
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PREPARE = runpy.run_path(str(Path(__file__).parents[1] /
                            "scripts/virtual/prepare-first-user-boot.py"))["prepare"]


def fixture(tmp_path):
    boot = tmp_path / "boot"
    boot.mkdir()
    for name in ("kernel8.img", "config.txt"):
        (boot / name).write_bytes(b"fixture only")
    credentials = tmp_path / "private.json"
    credentials.write_text(json.dumps({"user": "abcdef", "password": secrets.token_urlsafe(32)}))
    return boot, credentials


def test_existing_boot_configuration_is_preserved(tmp_path):
    boot, credentials = fixture(tmp_path)
    existing = boot / "userconf.txt"
    existing.write_bytes(b"administrator fixture")
    with pytest.raises(ValueError, match="Preserve"):
        PREPARE(boot, credentials)
    assert existing.read_bytes() == b"administrator fixture"


def test_non_pi_directory_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="boot partition"):
        PREPARE(tmp_path, tmp_path / "unused")


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Linux image-builder OpenSSL required")
def test_stock_boot_file_contains_matching_crypt_hash_only(tmp_path):
    boot, credentials = fixture(tmp_path)
    assert shutil.which("openssl"), "Linux image builds require the installed OpenSSL"
    original = json.loads(credentials.read_text())
    PREPARE(boot, credentials)
    content = (boot / "userconf.txt").read_text()
    user, encoded = content.strip().split(":")
    assert user == original["user"] and original["password"] not in content
    salt = encoded.split("$")[2]
    checked = subprocess.run(
        ["openssl", "passwd", "-6", "-salt", salt, "-stdin"],
        input=original["password"].encode() + b"\n", capture_output=True, check=True, timeout=15,
    ).stdout.decode().strip()
    assert checked == encoded


def test_non_linux_builder_refuses_before_starting_any_program(tmp_path, monkeypatch):
    boot, credentials = fixture(tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    def unexpected(*args, **kwargs):
        pytest.fail("A Linux image fixture started a program on an unsupported host")
    monkeypatch.setattr(subprocess, "run", unexpected)
    with pytest.raises(ValueError, match="Linux image builder"):
        PREPARE(boot, credentials)
    assert not (boot / "userconf.txt").exists()
