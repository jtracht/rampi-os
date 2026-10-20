"""Per-user, atomic configuration. Secrets are never configuration values."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)
    return path


def atomic_json(path: Path, value: object) -> None:
    private_dir(path.parent)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".rampi-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "rampi"


def cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "rampi"


def safe_url(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Bitte eine HTTPS-Adresse ohne eingebettete Zugangsdaten angeben.")
    return value


@dataclass
class Host:
    name: str = "Windows"
    address: str = ""
    username: str = ""
    port: int = 22
    identity: str = ""
    project: str = ""
    resolution: str = "1280x720"

    @classmethod
    def from_form(cls, values: dict, base: Host | None = None) -> Host:
        data = asdict(base) if base else asdict(cls())
        for key in data:
            if key in values:
                data[key] = int(str(values[key])) if key == "port" else str(values[key])
        for key in ["address", "username", "identity"]:
            data[key] = data[key].strip()
        return cls(**data)

    def validate(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}", self.address):
            raise ValueError("Ungültiger Hostname oder IP-Adresse.")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@\\-]{0,127}", self.username):
            raise ValueError("Ungültiger Windows-Benutzername.")
        if isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise ValueError("Der SSH-Port muss zwischen 1 und 65535 liegen.")
        if not re.fullmatch(r"[0-9]{3,4}x[0-9]{3,4}", self.resolution):
            raise ValueError("Ungültige Bildschirmauflösung.")
        if self.identity and not Path(self.identity).expanduser().is_file():
            raise ValueError("Der gewählte SSH-Schlüssel existiert nicht.")
        if any(c in self.project for c in "\x00\r\n"):
            raise ValueError("Ungültiges Projektverzeichnis.")


@dataclass
class Settings:
    language: str = "de"
    setup_complete: bool = False
    active_host: int = 0
    hosts: list[Host] = field(default_factory=list)
    browser_url: str = "https://www.raspberrypi.com"
    board_source: str = ""
    board_kind: str = "json"
    board_token_key: str = ""
    board_columns: list[str] = field(default_factory=list)
    reduce_motion: bool = False

    @property
    def host(self) -> Host:
        if not self.hosts or not 0 <= self.active_host < len(self.hosts):
            raise ValueError("Zuerst einen Windows-Host in den Einstellungen einrichten.")
        host = self.hosts[self.active_host]
        host.validate()
        return host

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or config_home() / "settings.json"
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Die Konfiguration muss ein JSON-Objekt sein.")
        allowed = set(cls.__dataclass_fields__)
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"Unbekannte Einstellungen: {', '.join(sorted(unknown))}")
        raw["hosts"] = [Host(**h) for h in raw.get("hosts", [])]
        result = cls(**raw)
        safe_url(result.browser_url)
        if result.hosts:
            _ = result.host
        if result.board_kind not in {"json", "github", "trello", "jira", "asana", "notion"}:
            raise ValueError("Unbekannter Kanban-Connector.")
        result.validate_columns()
        return result

    def validate_columns(self) -> None:
        if (
            not isinstance(self.board_columns, list)
            or len(self.board_columns) > 32
            or any(
                not isinstance(c, str)
                or not c.strip()
                or c != c.strip()
                or len(c) > 80
                or any(ord(v) < 32 for v in c)
                for c in self.board_columns
            )
            or len(set(self.board_columns)) != len(self.board_columns)
        ):
            raise ValueError("Kanban-Spalten: höchstens 32 eindeutige Namen mit 1–80 Zeichen.")

    def save(self, path: Path | None = None) -> None:
        safe_url(self.browser_url)
        self.validate_columns()
        if self.hosts:
            _ = self.host
        atomic_json(path or config_home() / "settings.json", asdict(self))
