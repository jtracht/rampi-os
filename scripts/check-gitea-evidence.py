"""Fail closed on missing actual Gitea HTTPS/GTK acceptance artifacts."""

import argparse
import json
import re
import struct
from pathlib import Path


def check(directory: Path):
    environment = json.loads((directory / "gitea-environment.json").read_text(encoding="utf-8"))
    if (
        environment.get("image")
        != "docker.gitea.com/gitea:28.2.0@sha256:"
        # pragma: allowlist nextline secret - public official Gitea image SHA256
        "30777c91280d973fa02be48b1ade735bd6859e8f6f7af3b4444d519437852504"
        or not environment.get("version", "").startswith("gitea version 28.2.0 ")
        or environment.get("private_network") is not True
        or environment.get("published_ports") is not False
        or environment.get("read_only_write_denied_http") != 403
        or environment.get("page_size") != 1
        or environment.get("cards") != 2
        or environment.get("refresh") is not True
        or environment.get("offline") is not True
    ):
        raise ValueError("Missing actual pinned/private Gitea scope or write rejection")
    issues = environment.get("actual_server_issues", [])
    if (
        len(issues) != 2
        or {row.get("title") for row in issues} != {"Rampi first updated", "Rampi second"}
        or len({row.get("id") for row in issues}) != 2
        or not all(type(row.get("id")) is int and row["id"] > 0 for row in issues)
    ):
        raise ValueError("Actual Gitea issues differ from authorized fixture mutation")
    digest = (directory / "gitea-program-sha256.txt").read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{64}", digest) or environment.get("binary_sha256") != digest:
        raise ValueError("Missing actual Gitea client binary identity")
    for name in ("refresh", "offline"):
        for suffix in ("ready", "continue"):
            if (directory / f"gitea-{name}-{suffix}").read_text() != name:
                raise ValueError("Missing actual Gitea phase handshake")
    if "RAMPI_RUST_GITEA_LIVE_PAGE_OK" not in (directory / "gitea-live.log").read_text(
        encoding="utf-8"
    ):
        raise ValueError("Actual Gitea GTK/keyring acceptance missing")
    with (directory / "gitea-live.png").open("rb") as capture:
        header = capture.read(24)
    if (
        len(header) != 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or struct.unpack(">II", header[16:24]) != (1280, 720)
    ):
        raise ValueError("Missing actual Gitea compositor capture")
    return environment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
    print("PASS: actual Gitea HTTPS/keyring/GTK, read-only token, refresh and offline cache.")
