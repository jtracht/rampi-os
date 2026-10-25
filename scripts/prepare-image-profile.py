"""Apply Rampi's package selection to a fresh pinned pi-gen checkout only."""

import argparse
from pathlib import Path


def configure(root):
    packages = root / "stage2/01-sys-tweaks/00-packages"
    if packages.is_symlink() or not packages.is_file():
        raise ValueError("Expected regular pinned pi-gen Lite package list")
    original = packages.read_text()
    lines = original.splitlines(keepends=True)
    # Connect is an additional cloud remote-shell service, not a Rampi backend.
    # Its binary-only APT publication cannot meet this image's complete source
    # archive policy. Do not relax that policy or remove it from user devices.
    matches = [line for line in lines if line.strip() == "rpi-connect-lite"]
    if len(matches) != 1:
        raise ValueError("Pinned pi-gen Connect package selection changed")
    packages.write_text("".join(line for line in lines if line != matches[0]), newline="\n")
    print("Rampi image profile: omitted unused rpi-connect-lite before installation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    configure(parser.parse_args().checkout)
