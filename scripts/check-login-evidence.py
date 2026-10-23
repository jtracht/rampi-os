"""Require fresh, real graphical PAM sessions and source-bound native binaries."""

import argparse
import json
import re
from pathlib import Path

from PIL import Image


def visible_capture(picture: Path):
    with Image.open(picture) as image:
        image.load()
        if image.format != "PNG" or image.size != (1280, 720):
            raise ValueError("Invalid graphical capture: " + str(picture))
        # A cursor on an otherwise black compositor must never pass as the UI.
        raw = image.convert("RGB").tobytes()
        bright = sum(
            max(r, g, b) > 48 for r, g, b in zip(raw[::3], raw[1::3], raw[2::3], strict=True)
        )
        if bright < 2000:
            raise ValueError("Application surface has not been painted: " + str(picture))


def check(directory: Path, expected_binary: str | None = None):
    environment = json.loads((directory / "environment.json").read_text(encoding="utf-8"))
    if environment.get("architecture") not in {"amd64", "arm64"}:
        raise ValueError("Unsupported login test architecture")
    if environment.get("memory_mib") != 1024 or environment.get("cpus") != 4:
        raise ValueError("Unexpected virtual resource budget")
    for key, expected in [
        ("physical_devices", False),
        ("prepared_development_cache", False),
        ("resumed_development_guest", False),
        ("graphical_login", True),
    ]:
        if environment.get(key) is not expected:
            raise ValueError("Not fresh graphical software evidence: " + key)
    digest = environment.get("native_binary_sha256", "")
    if not re.fullmatch(r"[a-f0-9]{64}", digest) or expected_binary and expected_binary != digest:
        raise ValueError("Native binary digest mismatch")
    log = (directory / "serial.log").read_text(encoding="utf-8", errors="replace")
    for marker in [
        "RAMPI_GRAPHICAL_LOGIN_NO_UNAUTH_UI_OK",
        "RAMPI_GRAPHICAL_LOGIN_REJECT_OK",
        "RAMPI_GRAPHICAL_LOGIN_TWO_USERS_OK",
        "RAMPI_GRAPHICAL_LOGIN_OK",
    ]:
        if marker not in log:
            raise ValueError("Missing actual graphical login stage: " + marker)
    exits = re.findall(r"RAMPI_GUEST_EXIT=(\d+)", log)
    if not exits or exits[-1] != "0":
        raise ValueError("Login guest did not finish successfully")
    proof = json.loads((directory / "captures/login-proof.json").read_text(encoding="utf-8"))
    if not isinstance(proof, list) or len(proof) != 2:
        raise ValueError("Two authenticated user sessions are required")
    identities = set()
    for account in proof:
        uid = account.get("uid")
        if type(uid) is not int or not 1000 <= uid < 65534 or uid in identities:
            raise ValueError("Distinct ordinary Linux identities are required")
        identities.add(uid)
        if account.get("session_uid") != uid or account.get("config_uid") != uid:
            raise ValueError("Authenticated identity mismatch")
        if account.get("native_process") is not True or account.get("config_mode") != "0o700":
            raise ValueError("Native session or private configuration missing")
        if account.get("binary_sha256") != digest:
            raise ValueError("Guest executed a different native binary")
    for name in ["greeter", "rampi-login", "rampi-other"]:
        picture = directory / "captures" / (name + ".png")
        visible_capture(picture)
    return environment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary")
    options = parser.parse_args()
    check(options.directory, options.expected_binary)
    print("PASS: fresh graphical PAM login, two native user identities and private profiles.")
