"""Write the stock supported userconf.txt fixture into a disposable Pi boot partition."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def prepare(boot, credentials):
    if not all((boot / name).is_file() for name in ("kernel8.img", "config.txt")):
        raise ValueError("A mounted disposable Raspberry Pi boot partition is required")
    if any((boot / name).exists() or (boot / name).is_symlink()
           for name in ("userconf", "userconf.txt")):
        raise ValueError("Preserve an existing boot account configuration")
    values = json.loads(credentials.read_text())
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", values["user"]) or values["user"] == "root":
        raise ValueError("Invalid first-account fixture name")
    if not values["password"] or any(c in values["password"] for c in "\r\n\0"):
        raise ValueError("Invalid first-account fixture credential")
    result = subprocess.run(
        ["openssl", "passwd", "-6", "-stdin"], input=values["password"].encode() + b"\n",
        capture_output=True, check=True, timeout=15,
    )
    encoded = result.stdout.decode().strip()
    if not re.fullmatch(r"\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}", encoded):
        raise ValueError("Existing OpenSSL did not produce a supported crypt hash")
    target = boot / "userconf.txt"
    with open(target, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        stream.write(values["user"] + ":" + encoded + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boot", type=Path)
    parser.add_argument("credentials", type=Path)
    options = parser.parse_args()
    prepare(options.boot, options.credentials)
