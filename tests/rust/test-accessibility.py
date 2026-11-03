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
                click("System")
                save = ("Persönliche Einstellungen speichern" if language == "de"
                        else "Save personal settings")
                read_until(lambda r, save=save: save in buttons(r))
                click(save)
                done = "Vorgang abgeschlossen." if language == "de" else "Done."
                rows = read_until(lambda r, done=done: done in [n["name"] for n in r])
                capture(language, "feedback-saved", rows)
                notice = next(node for node, _ in visible_objects()
                              if node.getRoleName() == "label" and node.name == done)
                bounds = notice.queryComponent().getExtents(pyatspi.WINDOW_COORDS)
                image_path = destination / f"accessibility-{language}-feedback-saved.png"
                with Image.open(image_path) as png:
                    if not (0 <= bounds.y and bounds.y + bounds.height <= png.height):
                        raise RuntimeError("Operation feedback is clipped outside the output")
                click(back)
                rows = read_until(lambda r, done=done: "Host & SSH" in buttons(r)
                                  and done not in [n["name"] for n in r])
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
