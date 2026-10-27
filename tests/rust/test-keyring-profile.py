"""Actual unprivileged profile preservation in a disposable Linux container."""

import os
import pwd
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if not Path("/.dockerenv").exists() or os.geteuid() != 0:
    raise SystemExit("Disposable root test container required")
account = pwd.getpwnam("rampi")
helper = ROOT / "installer/raspberrypi/keyring-profile-user.sh"
template = ROOT / "system/rampi-keyring-ordering.conf"


def run(*args, data=None):
    return subprocess.run(args, input=data, capture_output=True, check=True, timeout=30)


def as_user(*args, data=None):
    return run("runuser", "-u", "rampi", "--", *map(str, args), data=data)


def apply(profile_home, mode="--install"):
    as_user("sh", helper, mode, template, profile_home)


def target(profile_home):
    return (
        profile_home
        / ".config/systemd/user/gnome-keyring-daemon.service.d/50-rampi-pam-ordering.conf"
    )


def write(path, data):
    as_user("mkdir", "-p", path.parent)
    as_user("tee", path, data=data)


with tempfile.TemporaryDirectory(prefix="rampi-profile-test-", dir="/home/rampi") as directory:
    base = Path(directory)
    os.chown(base, account.pw_uid, account.pw_gid)
    homes = {}
    for name in ["fresh", "custom-unit", "custom-dropin", "keyring", "symlink"]:
        profile_home = base / name
        as_user("mkdir", "-m", "700", profile_home)
        homes[name] = profile_home
    fresh = homes["fresh"]
    apply(fresh)
    assert target(fresh).read_bytes() == template.read_bytes()
    assert target(fresh).stat().st_uid == account.pw_uid
    timestamp = target(fresh).stat().st_mtime_ns
    apply(fresh)
    assert target(fresh).stat().st_mtime_ns == timestamp
    custom = template.read_bytes() + b"# personal modification\n"
    write(target(fresh), custom)
    apply(fresh, "--remove")
    assert target(fresh).read_bytes() == custom
    write(target(fresh), template.read_bytes())
    apply(fresh, "--remove")
    assert not target(fresh).exists()

    unit = homes["custom-unit"] / ".config/systemd/user/gnome-keyring-daemon.service"
    write(unit, b"existing personal unit\n")
    dropin = target(homes["custom-dropin"]).with_name("custom.conf")
    write(dropin, b"existing personal drop-in\n")
    keyring = homes["keyring"] / ".local/share/keyrings/login.keyring"
    write(keyring, b"synthetic existing file, not real keyring acceptance\n")
    outside = base / "outside"
    as_user("mkdir", "-m", "700", outside)
    as_user("ln", "-s", outside, homes["symlink"] / ".config")
    for name in ["custom-unit", "custom-dropin", "keyring", "symlink"]:
        apply(homes[name])
        assert not target(homes[name]).exists()
    assert unit.read_bytes() == b"existing personal unit\n"
    assert dropin.read_bytes() == b"existing personal drop-in\n"
    assert keyring.read_bytes().startswith(b"synthetic existing file")
    assert not list(outside.iterdir())

# Exercise the real root dispatcher from a checkout unreadable by the user.
with tempfile.TemporaryDirectory(prefix="rampi-private-installer-") as directory:
    private = Path(directory)
    for name in [
        "installer/raspberrypi/keyring-profile.sh",
        "installer/raspberrypi/keyring-profile-user.sh",
        "system/rampi-keyring-ordering.conf",
    ]:
        dest = private / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    dispatcher = private / "installer/raspberrypi/keyring-profile.sh"
    run("bash", str(dispatcher), "--install")
    assert target(Path("/etc/skel")).read_bytes() == template.read_bytes()
    assert target(Path(account.pw_dir)).stat().st_uid == account.pw_uid
    run("bash", str(dispatcher), "--remove")
    assert not target(Path("/etc/skel")).exists()
    assert not target(Path(account.pw_dir)).exists()
    global_custom = Path("/etc/systemd/user/gnome-keyring-daemon.service.d/custom.conf")
    global_custom.parent.mkdir(parents=True, exist_ok=True)
    global_custom.write_text("# custom global configuration\n")
    run("bash", str(dispatcher), "--install")
    assert not target(Path("/etc/skel")).exists()
    assert global_custom.read_text() == "# custom global configuration\n"
    global_custom.unlink()
    packaged_unit = Path("/usr/lib/systemd/user/gnome-keyring-daemon.service")
    original_unit = packaged_unit.read_bytes()
    packaged_unit.write_bytes(original_unit + b"\n# locally modified package file\n")
    run("bash", str(dispatcher), "--install")
    assert not target(Path("/etc/skel")).exists()
    assert packaged_unit.read_bytes() == original_unit + b"\n# locally modified package file\n"
    packaged_unit.write_bytes(original_unit)
    relocated_unit = packaged_unit.with_name("fixture-original.service")
    packaged_unit.rename(relocated_unit)
    packaged_unit.symlink_to(relocated_unit)
    run("bash", str(dispatcher), "--install")
    assert not target(Path("/etc/skel")).exists()
    packaged_unit.unlink()
    relocated_unit.rename(packaged_unit)
    metadata = Path(
        run("dpkg-query", "--control-path", "gnome-keyring", "md5sums").stdout.decode().strip()
    )
    metadata.rename(metadata.with_name("fixture-hidden-md5sums"))
    run("bash", str(dispatcher), "--install")
    assert not target(Path("/etc/skel")).exists()
    metadata.with_name("fixture-hidden-md5sums").rename(metadata)

# The image's original first account exists before /etc/skel is configured and
# can still have nologin. Stock userconf later renames it and enables its shell.
# Exercise those real distribution tools and the same existing dispatcher.
with tempfile.TemporaryDirectory(prefix="rampi-first-profile-") as directory:
    initial, renamed = "rampi-bootstrap-initial", "rampi-bootstrap-ready"
    run("useradd", "--create-home", "--user-group", "--shell", "/usr/sbin/nologin",
        "--key", "UMASK=077", initial)
    home = Path(pwd.getpwnam(initial).pw_dir)
    assert not target(home).exists()
    run("bash", str(ROOT / "installer/raspberrypi/keyring-profile.sh"), "--install")
    assert not target(home).exists(), "A disabled account was unexpectedly modified"
    new_home = Path("/home") / renamed
    run("usermod", "--login", renamed, "--move-home", "--home", str(new_home),
        "--shell", "/bin/bash", initial)
    run("bash", str(ROOT / "installer/raspberrypi/keyring-profile.sh"), "--install")
    profile = target(new_home)
    assert profile.read_bytes() == template.read_bytes()
    assert profile.stat().st_uid == pwd.getpwnam(renamed).pw_uid
    before = (profile.stat().st_ino, profile.stat().st_mtime_ns)
    run("bash", str(ROOT / "installer/raspberrypi/keyring-profile.sh"), "--install")
    assert (profile.stat().st_ino, profile.stat().st_mtime_ns) == before
    print("RAMPI_FIRST_ACCOUNT_KEYRING_PROFILE_OK")
print("RAMPI_KEYRING_PROFILE_PRESERVATION_OK")
