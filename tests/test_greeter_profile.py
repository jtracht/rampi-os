"""An auth-profile update must preserve locally changed login configurations."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Linux installer file semantics")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("customized", ["none", "config", "profile", "symlink"])
def test_migrate_only_unchanged_managed_profile(tmp_path, customized):
    config = tmp_path / "greetd.toml"
    marker = tmp_path / "managed.sha256"
    profile = tmp_path / "greeter.xml"
    config.write_text('[default_session]\nuser = "_greetd"\n')
    marker.write_text(hashlib.sha256(config.read_bytes()).hexdigest() + "\n")
    original = (ROOT / "system/labwc/rc.xml").read_bytes()
    profile.write_bytes(original)
    if customized == "config":
        config.write_text("locally chosen login command\n")
    elif customized == "profile":
        profile.write_bytes(b"<labwc_config><!-- local choices --></labwc_config>")
    elif customized == "symlink":
        linked = tmp_path / "my-profile.xml"
        profile.rename(linked)
        profile.symlink_to(linked)
    before = profile.read_bytes()
    result = subprocess.run(
        [
            "bash",
            "-ec",
            'source "$1"; rampi_migrate_greeter_profile "$2" "$3" "$4" "$5"',
            "test",
            str(ROOT / "installer/raspberrypi/greeter-profile.sh"),
            str(ROOT),
            str(config),
            str(marker),
            str(profile),
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    expected = (ROOT / "system/labwc/greeter.xml").read_bytes() if customized == "none" else before
    assert profile.read_bytes() == expected
    if customized == "symlink":
        assert profile.is_symlink()
