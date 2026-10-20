"""Small adapters to XRandR and XKB in the existing X11 session."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .process import command


def snapshot() -> dict:
    if os.name != "posix" or not os.environ.get("DISPLAY"):
        raise RuntimeError("Anzeige und Eingabe benötigen die Linux-X11-Sitzung.")
    displays: list[dict] = []
    current: dict | None = None
    for line in command(["xrandr", "--query"]).splitlines():
        if match := re.match(r"^(\S+) connected\b", line):
            current = {"name": match[1], "modes": [], "current": ""}
            displays.append(current)
        elif line and not line[0].isspace():
            current = None
        elif current is not None and (match := re.match(r"\s+(\d+x\d+)\s+(.+)", line)):
            current["modes"].append(match[1])
            if "*" in match[2]:
                current["current"] = match[1]
    layouts = []
    in_layouts = False
    for line in Path("/usr/share/X11/xkb/rules/evdev.lst").read_text().splitlines():
        if line.startswith("!"):
            in_layouts = line.strip() == "! layout"
        elif in_layouts and (match := re.match(r"\s+([a-z0-9]+)\s+(.+)", line)):
            layouts.append({"key": match[1], "label": match[2]})
    keyboard = dict(
        line.strip().split(":", 1) for line in command(["setxkbmap", "-query"]).splitlines()
    )
    return {
        "displays": displays,
        "layouts": layouts,
        "layout": keyboard.get("layout", "").strip(),
        "error": "",
    }


def resolution(output: str, mode: str) -> str:
    available = next((d for d in snapshot()["displays"] if d["name"] == output), None)
    if not available or mode not in available["modes"]:
        raise ValueError("Diese Anzeige oder Auflösung ist nicht mehr verfügbar.")
    command(["xrandr", "--output", output, "--mode", mode])
    return "Auflösung für die laufende Sitzung übernommen."


def keyboard(layout: str) -> str:
    if layout not in {row["key"] for row in snapshot()["layouts"]}:
        raise ValueError("Unbekanntes Tastaturlayout.")
    command(["setxkbmap", "-layout", layout])
    return "Tastaturlayout für die laufende Sitzung übernommen."


def pointer(speed: int) -> str:
    if isinstance(speed, bool) or not 1 <= speed <= 5:
        raise ValueError("Mausgeschwindigkeit muss zwischen 1 und 5 liegen.")
    if os.name != "posix" or not os.environ.get("DISPLAY"):
        raise RuntimeError("Die Maussteuerung benötigt die Linux-X11-Sitzung.")
    command(["xset", "m", str(speed), "4"])
    return "Mausbeschleunigung für die laufende Sitzung übernommen."
