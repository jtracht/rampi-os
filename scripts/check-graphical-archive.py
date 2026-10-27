"""Validate the exact public image evidence archive, including pristine first login."""

import argparse
import runpy
import tarfile
import tempfile
from pathlib import Path

FILES = (
    "environment.json", "serial.log", "captures/login-proof.json",
    "captures/greeter.png", "captures/rampi-login.png", "captures/rampi-other.png",
    "captures/first-user-proof.json", "captures/first-user.png",
    "captures/first-user-precredential-input.log",
    "captures/first-user-reboot-proof.json", "captures/first-user-reboot.png",
)
FILES += tuple("preconfigured/" + name for name in (
    "environment.json", "serial.log", "captures/first-user-proof.json",
    "captures/first-user.png", "captures/first-user-reboot-proof.json",
    "captures/first-user-reboot.png",
))
PREFIX = "graphical-login/"


def read_members(path):
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        expected = {PREFIX + name for name in FILES}
        if len(members) != len(expected) or {member.name for member in members} != expected:
            raise ValueError(
                "Image evidence must include exactly the approved login/first-user files"
            )
        result = {}
        for member in members:
            limit = 24 * 1024 * 1024 if member.name.endswith(".png") else 8 * 1024 * 1024
            if not member.isfile() or not 0 < member.size <= limit:
                raise ValueError("Image evidence must contain bounded regular files")
            result[member.name] = archive.extractfile(member).read(limit + 1)
            if len(result[member.name]) != member.size:
                raise ValueError("Truncated image evidence file")
    return result


def check(path, revision, image_sha256, binary_sha256):
    files = read_members(path)
    with tempfile.TemporaryDirectory(prefix="rampi-public-image-evidence-") as directory:
        root = Path(directory)
        for name, content in files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        report = runpy.run_path(str(Path(__file__).with_name("check-image-login-evidence.py")))[
            "check"
        ](root / "graphical-login", revision, image_sha256)
        if report["native_binary_sha256"] != binary_sha256:
            raise ValueError("Published graphical evidence used another native program")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image-sha256", required=True)
    parser.add_argument("--binary-sha256", required=True)
    options = parser.parse_args()
    check(options.archive, options.revision, options.image_sha256, options.binary_sha256)
    print("PASS: published pristine first-user/PAM and two-account graphical evidence.")
