"""OpenSSH host-key enrollment, with explicit independent fingerprint verification."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from .config import Host, private_dir
from .process import command


def lookup_name(host: Host) -> str:
    host.validate()
    return host.address if host.port == 22 else f"[{host.address}]:{host.port}"


def key_material(lines: str) -> set[tuple[str, str]]:
    result = set()
    for line in lines.splitlines():
        if line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 3 and fields[1] in {"ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256"}:
            if re.fullmatch(r"[A-Za-z0-9+/=]+", fields[2]):
                result.add((fields[1], fields[2]))
    return result


def scan(host: Host) -> dict:
    name = lookup_name(host)
    output = command(
        ["ssh-keyscan", "-T", "5", "-p", str(host.port), "-t", "ed25519,ecdsa,rsa", host.address],
        timeout=20,
    )
    material = key_material(output)
    if not material:
        raise ValueError("Der Host hat keine verwendbaren OpenSSH-Hostschlüssel geliefert.")
    lines = "\n".join(f"{name} {kind} {key}" for kind, key in sorted(material)) + "\n"
    with tempfile.TemporaryDirectory(prefix="rampi-hostkey-") as directory:
        path = Path(directory) / "public-keys"
        path.write_text(lines, encoding="utf-8")
        fingerprints = command(["ssh-keygen", "-l", "-f", str(path), "-E", "sha256"])
    return {"address": host.address, "port": host.port, "fingerprints": fingerprints, "keys": lines}


def trust(host: Host, candidate: dict, directory: Path | None = None) -> str:
    name = lookup_name(host)
    if candidate.get("address") != host.address or candidate.get("port") != host.port:
        raise ValueError("Der Host wurde geändert. Bitte die Fingerprints erneut abrufen.")
    material = key_material(str(candidate.get("keys", "")))
    if not material:
        raise ValueError("Zuerst die Hostschlüssel abrufen und unabhängig vergleichen.")
    target = private_dir(directory or Path.home() / ".ssh") / "known_hosts"
    if target.exists():
        existing = subprocess.run(
            ["ssh-keygen", "-F", name, "-f", str(target)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if existing.returncode not in {0, 1}:
            raise RuntimeError("Vorhandene OpenSSH-Hostkonfiguration konnte nicht geprüft werden.")
        found = key_material(existing.stdout)
        if found:
            if material.issubset(found):
                return "Diese Hostschlüssel sind bereits bekannt."
            raise ValueError(
                "Andere Hostschlüssel sind bereits gespeichert. Keine Änderung; "
                "eine Schlüsselrotation muss unabhängig geprüft werden."
            )
    data = "\n" + "\n".join(f"{name} {kind} {key}" for kind, key in sorted(material)) + "\n"
    fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, data.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    return "Unabhängig geprüfte Hostschlüssel im persönlichen OpenSSH-Profil gespeichert."
