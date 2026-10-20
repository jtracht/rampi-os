"""Only fixed executables and argument arrays; SSH remains the authentication boundary."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

from .config import Host, Settings, config_home, private_dir, safe_url

MODULES = ("codex", "claude", "antigravity")


def executable(*names: str) -> str:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(f"Nicht installiert: {' / '.join(names)}")


def ps_literal(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Nullzeichen sind nicht erlaubt.")
    return "'" + value.replace("'", "''") + "'"


def ssh_args(host: Host, module: str) -> list[str]:
    host.validate()
    if module not in MODULES:
        raise ValueError("Unbekanntes KI-Modul.")
    script = (
        "$ErrorActionPreference='Stop'; "
        "$s=Join-Path $env:LOCALAPPDATA 'Rampi\\rampi-session.ps1'; "
        f"& $s -Module {ps_literal(module)} -Project {ps_literal(host.project)}; "
        "exit $LASTEXITCODE"
    )
    return ssh_command(host, script)


def preview_args(host: Host, module: str) -> list[str]:
    if module not in MODULES:
        raise ValueError("Unbekanntes KI-Modul.")
    script = (
        "$ErrorActionPreference='Stop'; "
        f"psmux.exe capture-pane -p -t {ps_literal('rampi-' + module)}; exit $LASTEXITCODE"
    )
    return ssh_command(host, script, interactive=False)


def ssh_command(host: Host, script: str, interactive: bool = True) -> list[str]:
    host.validate()
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    args = [
        "ssh",
        "-tt" if interactive else "-T",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectTimeout=8",
        "-p",
        str(host.port),
    ]
    if not interactive:
        args += ["-o", "BatchMode=yes"]
    if host.identity:
        args += ["-i", str(Path(host.identity).expanduser())]
    args += [
        "-l",
        host.username,
        host.address,
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-EncodedCommand",
        encoded,
    ]
    return args


def terminal_args(args: list[str], title: str) -> list[str]:
    terminal = executable("xfce4-terminal")
    return [
        terminal,
        "--disable-server",
        "--fullscreen",
        "--title",
        f"Rampi · {title}",
        "--execute",
        *args,
    ]


def browser_args(settings: Settings) -> list[str]:
    url = safe_url(settings.browser_url)
    browser = executable("chromium", "chromium-browser", "firefox", "firefox-esr")
    profile = config_home() / "browser"
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    if "firefox" in Path(browser).name:
        return [browser, "--no-remote", "--profile", str(profile), url]
    return [browser, f"--user-data-dir={profile}", "--start-fullscreen", url]


def rdp_args(host: Host) -> list[str]:
    host.validate()
    # FreeRDP asks interactively for credentials; never use /p or /cert:ignore.
    return [
        executable("xfreerdp3", "xfreerdp"),
        f"/v:{host.address}",
        f"/u:{host.username}",
        "/f",
        "/dynamic-resolution",
        "/network:auto",
        "/cert:tofu",
        "-grab-keyboard",
        "/bpp:24",
    ]


def stream_profile(host: Host) -> Path:
    """Never reuse paired-client credentials across Windows account/host profiles."""
    host.validate()
    identity = json.dumps([host.address.casefold(), host.port, host.username.casefold()])
    name = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    root = private_dir(private_dir(config_home()) / "streaming")
    path = private_dir(root / name)
    # Moonlight Embedded 2.7.1 copies this option into a 4096-byte C buffer.
    if len(os.fsencode(path)) >= 4096:
        raise ValueError("Der Pfad zum Streaming-Profil ist zu lang.")
    return path


def pair_args(host: Host) -> list[str]:
    return [executable("moonlight"), "pair", "-keydir", str(stream_profile(host)), host.address]


def stream_args(host: Host) -> list[str]:
    host.validate()
    width, height = host.resolution.split("x")
    # Moonlight Embedded CLI (not moonlight-qt, which has a different CLI).
    return [
        executable("moonlight"),
        "stream",
        "-keydir",
        str(stream_profile(host)),
        "-platform",
        "sdl",
        "-width",
        width,
        "-height",
        height,
        "-fps",
        "30",
        "-bitrate",
        "5000",
        "-app",
        "Desktop",
        host.address,
    ]
