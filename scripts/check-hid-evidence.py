"""Require fresh, source-bound real HID/GTK evidence; never accept debug guests."""

import argparse
import hashlib
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Public Google Bumble source commit from its upstream Git metadata.
SDK = "e1fe43c9b44be0d974a6fd533ac6d494fc50510a"  # pragma: allowlist secret
SOURCES = [
    "scripts/virtual/test-hid-guest.py",
    "scripts/virtual/bluetooth-hid-peer.py",
    "scripts/virtual/hid-layout-oracle.py",
    "scripts/virtual/hid-accessible-state.py",
    "scripts/virtual/hid-rdp-stage.py",
]
KEYS = [(4, 0), (28, 0), (29, 0), (31, 2), (8, 64)]
# Independently read from the installed Debian libxkbcommon, outside Rampi.
GLYPHS = {
    "de": ["a", "z", "y", '"', "€"],
    "us": ["a", "y", "z", "@", ""],
    "gb": ["a", "y", "z", '"', "e"],
    "fr": ["q", "y", "w", "2", "€"],
    "es": ["a", "y", "z", '"', "€"],
    "it": ["a", "y", "z", '"', "€"],
}


def validate_proof(proof, expected_binary):
    if proof.get("schema") != 1 or proof.get("sdk_revision") != SDK:
        raise ValueError("Missing pinned HID SDK/schema provenance")
    if proof.get("native_elf_sha256") != expected_binary:
        raise ValueError("HID sessions executed another program")
    if proof.get("complete_product_acceptance") is not False:
        raise ValueError("HID evidence must not claim whole-product acceptance")
    for key in [
        "two_personal_layout_files_private",
        "actual_ui_pair_trust_connect_reconnect_forget",
    ]:
        if proof.get(key) is not True:
            raise ValueError("Incomplete real HID stage: " + key)
    for name in SOURCES:
        expected = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if proof.get("source_hashes", {}).get(name) != expected:
            raise ValueError("HID evidence source mismatch: " + name)
    sessions = proof.get("sessions")
    if not isinstance(sessions, list) or len(sessions) != 6:
        raise ValueError("Exactly six actual personal layout sessions are required")
    layouts, identities = set(), {}
    for session in sessions:
        layout, user, uid = (session.get(k) for k in ["layout", "user", "uid"])
        if layout not in GLYPHS or layout in layouts:
            raise ValueError("Missing or duplicate HID layout")
        layouts.add(layout)
        expected_user = "rampi-hid-one" if layout in {"de", "us", "gb"} else "rampi-hid-two"
        if (
            user != expected_user
            or type(uid) is not int
            or not 1000 <= uid < 65534
            or user in identities
            and identities[user] != uid
        ):
            raise ValueError("Actual HID/PAM user identity mismatch")
        identities[user] = uid
        if (
            type(session.get("native_pid")) is not int
            or session["native_pid"] <= 1
            or session.get("native_elf_sha256") != expected_binary
            or session.get("gtk_accessibility_backend") != "atspi"
        ):
            raise ValueError("Actual HID account process/program binding missing")
        for key in ["mouse_back", "reserved_shortcut", "actual_reconnect", "accessible_field_name"]:
            if session.get(key) is not True:
                raise ValueError("Missing actual HID interaction: " + key)
        nodes = session.get("kernel_bluetooth_input_nodes", {})
        if (
            set(nodes) != {"keyboard", "mouse"}
            or len(set(nodes.values())) != 2
            or any(
                not isinstance(n, str) or not re.fullmatch(r"/dev/input/event[0-9]+", n)
                for n in nodes.values()
            )
        ):
            raise ValueError("Actual kernel Bluetooth keyboard and mouse nodes required")
        keys = session.get("keys")
        if not isinstance(keys, list) or len(keys) != len(KEYS):
            raise ValueError("All actual HID modifier/glyph cases are required")
        for observed, (usage, modifiers), glyph in zip(keys, KEYS, GLYPHS[layout], strict=True):
            if (
                type(observed.get("usage")) is not int
                or observed["usage"] != usage
                or type(observed.get("modifiers")) is not int
                or observed["modifiers"] != modifiers
                or observed.get("actual") != glyph
                or observed.get("expected") != glyph
            ):
                raise ValueError("Actual HID input does not match the independent XKB case")
    if len({s["native_pid"] for s in sessions}) != 6:
        raise ValueError("Six actual fresh authenticated application processes required")
    if len(identities) != 2 or len(set(identities.values())) != 2:
        raise ValueError("Two distinct real HID users are required")
    return sessions


def check_cursor_images(captures, proof):
    from PIL import Image

    for session in proof["sessions"]:
        stem = session["user"] + "-" + session["layout"]
        for state, key in [("keyboard", "keyboard_cursor"), ("mouse", "mouse_cursor")]:
            observed = session.get(key, {})
            names = [stem + "-" + state + suffix for suffix in ["-plain.png", "-cursor.png"]]
            if [observed.get("plain"), observed.get("overlay")] != names:
                raise ValueError("Actual cursor image identity missing")
            area = observed.get("area", [])
            if len(area) != 4 or any(type(v) is not int for v in area):
                raise ValueError("Actual cursor bounds missing")
            with (
                Image.open(captures / names[0]) as first,
                Image.open(captures / names[1]) as second,
            ):
                a, b = first.convert("RGB"), second.convert("RGB")
                if a.size != b.size or not (
                    0 <= area[0] < area[2] <= a.width and 0 <= area[1] < area[3] <= a.height
                ):
                    raise ValueError("Actual cursor capture bounds invalid")
                if area[2] - area[0] != 128 or not 8 <= area[3] - area[1] <= 100:
                    raise ValueError("Actual cursor field region invalid")
                count = sum(
                    sum(
                        abs(x - y)
                        for x, y in zip(a.getpixel((px, py)), b.getpixel((px, py)), strict=True)
                    )
                    > 60
                    for px in range(area[0], area[2])
                    for py in range(area[1], area[3])
                )
                reference = area[2] + 32
                if reference >= b.width:
                    raise ValueError("Actual cursor reference outside image")
                visible = sum(
                    sum(
                        abs(x - y)
                        for x, y in zip(
                            b.getpixel((px, py)), b.getpixel((reference, py)), strict=True
                        )
                    )
                    > 60
                    for px in range(area[0], area[2])
                    for py in range(area[1], area[3])
                )
            if (
                count != observed.get("overlay_difference_pixels")
                or visible != observed.get("pixels")
                or (state == "keyboard" and visible != 0)
                or (state == "mouse" and visible < 5)
            ):
                raise ValueError("Actual cursor visibility mismatch")


def check(directory, expected_binary=None):
    login = runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))
    environment = login["check"](directory, expected_binary)
    binary = environment["native_binary_sha256"]
    log = (directory / "serial.log").read_text(encoding="utf-8", errors="replace")
    if "RAMPI_ACTUAL_HID_GUI_SIX_LAYOUTS_TWO_USERS_OK" not in log:
        raise ValueError("Actual complete HID guest stage did not finish")
    captures = directory / "captures/hid"
    proof = json.loads((captures / "hid-proof.json").read_text(encoding="utf-8"))
    sessions = validate_proof(proof, binary)
    check_cursor_images(captures, proof)
    keycodes = [30, 21, 44, 3, 18]
    for session in sessions:
        stem = session["user"] + "-" + session["layout"]
        trace = (captures / (stem + "-kernel-keyboard.txt")).read_bytes()
        previous = 0
        for observed, keycode in zip(session["keys"], keycodes, strict=True):
            start, end = observed.get("kernel_offset_start"), observed.get("kernel_offset_end")
            if (
                type(start) is not int
                or type(end) is not int
                or not previous <= start < end <= len(trace)
            ):
                raise ValueError("Actual evtest receipt range missing or overlapping")
            previous = end
            events = {
                (int(code), int(value))
                for code, value in re.findall(
                    r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]+\), value ([012])",
                    trace[start:end].decode("utf-8", errors="replace"),
                )
            }
            modifier = {2: 42, 64: 100}.get(observed["modifiers"])
            for code in [keycode] + ([modifier] if modifier is not None else []):
                if not {(code, 0), (code, 1)} <= events:
                    raise ValueError("Actual kernel HID key/modifier receipt missing")
        for suffix in ["hid-text", "hid-mouse", "hid-shortcut"]:
            login["visible_capture"](captures / (stem + "-" + suffix + ".png"))
        accessible = json.loads(
            (captures / (stem + "-accessible.json")).read_text(encoding="utf-8")
        )
        if not isinstance(accessible, list) or not any(
            row.get("role") in {"text", "entry"} and row.get("name") == "Profilname"
            for row in accessible
        ):
            raise ValueError("Actual GTK form field accessibility metadata missing")
        dashboard = json.loads(
            (captures / (stem + "-dashboard-accessible.json")).read_text(encoding="utf-8")
        )
        names = [r.get("name", "") for r in dashboard if r.get("role") == "button"]
        if not (
            "Kanban Board" in names
            and any(n.startswith("WLAN") for n in names)
            and any(
                n.replace("\u2068", "").replace("\u2069", "") == "Bluetooth · 1 verbunden"
                for n in names
            )
        ):
            raise ValueError("Actual named dashboard status controls missing")
    for name in ["trust-confirmation", "forget-confirmation"]:
        login["visible_capture"](captures / (name + ".png"))
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary")
    args = parser.parse_args()
    check(args.directory, args.expected_binary)
    print("PASS: fresh actual HID, GTK, six layouts, two PAM users, reconnect and forget.")
