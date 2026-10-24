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


@pytest.mark.parametrize("customized", ["none", "config", "profile", "colors", "marker", "symlink"])
def test_branding_migration_preserves_local_configuration(tmp_path, customized):
    config, marker, profile, colors = [
        tmp_path / name for name in ["greetd", "hash", "rc", "colors"]
    ]
    config.write_bytes((ROOT / "system/greetd-unbranded.toml").read_bytes())
    marker.write_text(hashlib.sha256(config.read_bytes()).hexdigest() + "\n")
    profile.write_bytes((ROOT / "system/labwc/greeter.xml").read_bytes())
    if customized == "config":
        config.write_text("# local changes\n" + config.read_text())
    elif customized == "profile":
        profile.write_text("<!-- local profile -->")
    elif customized == "colors":
        colors.write_text("# my colors")
    elif customized == "marker":
        marker.write_text("0" * 64)
    elif customized == "symlink":
        colors.symlink_to(tmp_path / "unrelated")
    before = config.read_bytes()
    previous_marker = marker.read_bytes()
    for _ in range(2):
        subprocess.run(
            [
                "bash",
                "-ec",
                'source "$1"; rampi_migrate_greeter_branding "$2" "$3" "$4" "$5" "$6"',
                "test",
                str(ROOT / "installer/raspberrypi/greeter-profile.sh"),
                str(ROOT),
                str(config),
                str(marker),
                str(profile),
                str(colors),
            ],
            check=True,
        )
    if customized == "none":
        assert config.read_bytes() == (ROOT / "system/greetd.toml").read_bytes()
        assert marker.read_text().strip() == hashlib.sha256(config.read_bytes()).hexdigest()
        assert colors.read_bytes() == (ROOT / "system/wlgreet.toml").read_bytes()
    else:
        assert config.read_bytes() == before
        assert marker.read_bytes() == previous_marker
        if customized == "symlink":
            assert colors.is_symlink()
        elif customized == "colors":
            assert colors.read_text() == "# my colors"
        else:
            assert not colors.exists()
