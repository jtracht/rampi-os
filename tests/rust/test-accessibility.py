"""Exercise actual GTK/AT-SPI captions in the isolated Wayland test session."""

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pyatspi
from gi.repository import GLib
from PIL import Image

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or os.environ.get("DISPLAY"):
    raise SystemExit("Isolated Wayland test container required")

ROOT = Path(__file__).resolve().parents[2]
accessibility = runpy.run_path(str(ROOT / "scripts/virtual/hid-accessible-state.py"))
snapshot = accessibility["snapshot"]
visible_objects = accessibility["visible_objects"]
binary = Path("/build/target/debug/rampi-native")
destination = Path(os.environ.get("RAMPI_TEST_ARTIFACTS") or tempfile.mkdtemp(prefix="rampi-a11y-"))
destination.mkdir(exist_ok=True, parents=True)
expected_fields = {
    "de": {
        "Profilname",
        "Hostname / VPN-IP",
        "Windows-Benutzername",
        "SSH-Port",
        "Privater SSH-Schlüssel · Dateipfad",
        "Streaming-Auflösung · z. B. 1280x720",
    },
    "en": {
        "Profile name",
        "Hostname / VPN IP",
        "Windows username",
        "SSH port",
        "Private SSH key · file path",
        "Streaming resolution · e.g. 1280x720",
    },
}


def read_until(predicate):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        rows = snapshot()
        last = destination / "accessibility-last-observed.json"
        last.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        last.chmod(0o644)
        if predicate(rows) and all(name.strip() for name in buttons(rows)):
            return rows
        time.sleep(0.15)
    raise RuntimeError("Actual accessible page did not become ready")


def buttons(rows):
    return [row["name"] for row in rows if row["role"] == "button"]


def click(caption):
    accessibility["activate_control"](caption)


def capture(language, page, rows):
    # Names and roles only: never read text contents or password values.
    if any(not name.strip() for name in buttons(rows)):
        raise RuntimeError("An actual visible button has no accessible caption")
    stem = destination / f"accessibility-{language}-{page}"
    stem.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    stem.with_suffix(".json").chmod(0o644)
    # The native page crossfade is 150 ms; capture its settled rendered page.
    time.sleep(0.2)
    subprocess.run(["grim", str(stem.with_suffix(".png"))], check=True)
    stem.with_suffix(".png").chmod(0o644)


sessions = []
for language in ["de", "en"]:
    with tempfile.TemporaryDirectory(prefix="rampi-accessibility-") as folder:
        home = Path(folder)
        config = home / "config/rampi"
        config.mkdir(parents=True)
        (config / "settings.json").write_text(
            json.dumps(
                {
                    "language": language,
                    "setup_complete": True,
                    "sound_effects": False,
                    # A stored profile focuses the list first; require a real field click.
                    "hosts": [
                        {
                            "name": "Synthetic fixture",
                            "address": "fixture.invalid",
                            "username": "fixture",
                        }
                    ],
                }
            )
        )
        environment = dict(
            os.environ,
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / "config"),
            XDG_CACHE_HOME=str(home / "cache"),
            GTK_A11Y="atspi",
        )
        with (home / "application.log").open("w") as log:
            app = subprocess.Popen([str(binary)], env=environment, stdout=log, stderr=log)
            try:
                expected_binary = hashlib.sha256(binary.read_bytes()).hexdigest()
                if (
                    hashlib.sha256(Path(f"/proc/{app.pid}/exe").read_bytes()).hexdigest()
                    != expected_binary
                ):
                    raise RuntimeError("Accessibility test executed another program")
                wifi = "WLAN" if language == "de" else "Wi-Fi"
                rows = read_until(
                    lambda r, wifi=wifi: (
                        any(n.startswith(wifi) for n in buttons(r))
                        and any(n.startswith("Bluetooth") for n in buttons(r))
                    )
                )
                capture(language, "dashboard", rows)
                settings = next(n for n in buttons(rows) if "Einstellungen" in n or "Settings" in n)
                click(settings)
                rows = read_until(
                    lambda r, wifi=wifi: "Host & SSH" in buttons(r) and wifi in buttons(r)
                )
                capture(language, "categories", rows)
                click("Host & SSH")
                rows = read_until(
                    lambda r, language=language: (
                        expected_fields[language]
                        <= {n["name"] for n in r if n["role"] in {"text", "entry"}}
                    )
                )
                profile_caption = "Profilname" if language == "de" else "Profile name"
                field = next(
                    (
                        node
                        for node, _ in visible_objects()
                        if node.getRoleName() in {"text", "entry"} and node.name == profile_caption
                    ),
                    None,
                )
                if field is None:
                    raise RuntimeError("Actual visible synthetic profile field unavailable")
                typed = "a11y-" + language
                # GtkEntry exposes its text through a delegate; its outer accessible
                # does not implement GrabFocus. Click its actual visible bounds.
                bounds = accessibility["control_bounds"](profile_caption)
                for args in [
                    ("move", "-10000", "-10000"),
                    (
                        "move",
                        str(bounds["x"] + bounds["width"] // 2),
                        str(bounds["y"] + bounds["height"] // 2),
                    ),
                    ("click", "left"),
                ]:
                    subprocess.run(["wlrctl", "pointer", *args], check=True)
                subprocess.run(
                    [
                        "wtype",
                        "-s",
                        "100",
                        "-M",
                        "ctrl",
                        "-k",
                        "a",
                        "-m",
                        "ctrl",
                        "-k",
                        "BackSpace",
                    ],
                    check=True,
                )
                read_until(lambda rows, field=field: field.queryText().characterCount == 0)
                subprocess.run(["wtype", "-s", "100", typed], check=True)
                try:
                    read_until(
                        lambda rows, field=field, typed=typed: (
                            field.queryText().getText(0, field.queryText().characterCount) == typed
                        )
                    )
                except RuntimeError:
                    print(
                        "SYNTHETIC_PROFILE_FIELD_DEBUG",
                        repr(field.queryText().getText(0, field.queryText().characterCount)),
                        flush=True,
                    )
                    subprocess.run(
                        ["grim", str(destination / "synthetic-field-failed.png")], check=True
                    )
                    raise
                capture(language, "host", rows)
                back = "← Einstellungen" if language == "de" else "← Settings"
                click(back)
                read_until(lambda r: "System" in buttons(r))
                saved_host = json.loads((config / "settings.json").read_text())["hosts"]
                if len(saved_host) != 1 or saved_host[0]["name"] != typed:
                    raise RuntimeError("Page change lost the automatically saved host name")
                click("System")
                read_until(
                    lambda r: any(n["role"] in {"toggle button", "switch", "check box"} for n in r)
                )
                if any(
                    "speichern" in name.lower() or "save" in name.lower()
                    for name in buttons(snapshot())
                ):
                    raise RuntimeError("System settings still contain a save action")
                # Use the actual localized accessible switch captions from the widget tree.
                capture(language, "system", snapshot())
                switches = [
                    node
                    for node, _ in visible_objects()
                    if node.getRoleName() in {"toggle button", "switch", "check box"}
                ]
                if len(switches) != 2 or any(not node.name.strip() for node in switches):
                    raise RuntimeError("Two named native slide switches required")
                for active in [True, False]:
                    for node in switches:
                        state = node.getState().contains(pyatspi.STATE_CHECKED)
                        if state != active:
                            for _ in range(24):
                                if node.getState().contains(pyatspi.STATE_FOCUSED):
                                    break
                                subprocess.run(["wtype", "-s", "100", "-k", "Tab"], check=True)
                                time.sleep(0.03)
                            else:
                                raise RuntimeError("Native slide switch is not keyboard reachable")
                            subprocess.run(["wtype", "-s", "100", "-k", "space"], check=True)
                        read_until(
                            lambda r, node=node, active=active: (
                                node.getState().contains(pyatspi.STATE_CHECKED) == active
                            )
                        )
                    mode = "on" if active else "off"
                    capture(language, f"switches-{mode}", snapshot())
                    geometry = []
                    image_path = destination / f"accessibility-{language}-switches-{mode}.png"
                    with Image.open(image_path) as im:
                        for node in switches:
                            b = node.queryComponent().getExtents(pyatspi.WINDOW_COORDS)
                            geometry.append(
                                {
                                    "name": node.name,
                                    "x": b.x,
                                    "y": b.y,
                                    "width": b.width,
                                    "height": b.height,
                                }
                            )
                            region = im.convert("RGB").crop(
                                (b.x, b.y, b.x + b.width, b.y + b.height)
                            )
                            green = sum(
                                g > r + 30 and g > blue + 20 for r, g, blue in region.getdata()
                            )
                            if (active and green < 80) or (not active and green > 10):
                                raise RuntimeError("Slide switch track does not show actual state")
                    receipt = destination / (
                        f"accessibility-{language}-switches-{mode}-geometry.json"
                    )
                    receipt.write_text(json.dumps(geometry, ensure_ascii=False), encoding="utf-8")
                    receipt.chmod(0o644)
                persisted = json.loads((config / "settings.json").read_text())
                if persisted["reduce_motion"] or persisted["sound_effects"]:
                    raise RuntimeError("Native switches did not automatically persist")
                done = "Automatisch gespeichert" if language == "de" else "Saved automatically"
                rows = read_until(lambda r, done=done: done in [n["name"] for n in r])
                capture(language, "feedback-saved", rows)
                notice = next(
                    node
                    for node, _ in visible_objects()
                    if node.getRoleName() == "label" and node.name == done
                )
                bounds = notice.queryComponent().getExtents(pyatspi.WINDOW_COORDS)
                image_path = destination / f"accessibility-{language}-feedback-saved.png"
                with Image.open(image_path) as png:
                    if not (0 <= bounds.y and bounds.y + bounds.height <= png.height):
                        raise RuntimeError("Operation feedback is clipped outside the output")
                click(back)
                read_until(lambda r: "System" in buttons(r))
                click("System")
                read_until(
                    lambda r: (
                        len([n for n in r if n["role"] in {"toggle button", "switch", "check box"}])
                        == 2
                    )
                )
                if any(
                    node.getState().contains(pyatspi.STATE_CHECKED)
                    for node, _ in visible_objects()
                    if node.getRoleName() in {"toggle button", "switch", "check box"}
                ):
                    raise RuntimeError("Page return lost the automatically saved switches")
                click(back)
                rows = read_until(
                    lambda r, done=done: (
                        "Host & SSH" in buttons(r) and done not in [n["name"] for n in r]
                    )
                )
                capture(language, "feedback-cleared", rows)
                sessions.append(
                    {
                        "language": language,
                        "pid": app.pid,
                        "uid": os.getuid(),
                        "native_elf_sha256": expected_binary,
                    }
                )
            finally:
                app.terminate()
                app.wait(timeout=10)
                log.flush()
                public_log = destination / f"accessibility-{language}-application.log"
                shutil.copyfile(home / "application.log", public_log)
                public_log.chmod(0o644)

proof = {
    "schema": 1,
    "sessions": sessions,
    "complete_product_acceptance": False,
    "source_hashes": {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ["tests/rust/test-accessibility.py", "scripts/virtual/hid-accessible-state.py"]
    },
}
receipt = destination / "accessibility-proof.json"
receipt.write_text(json.dumps(proof, indent=2) + "\n")
receipt.chmod(0o644)
print("RAMPI_ACTUAL_GTK_A11Y_TWO_LANGUAGES_OK")
