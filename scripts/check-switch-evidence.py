"""Check actual native switch state, visible geometry and on/off track pixels."""

import json

from PIL import Image


def check(directory, expected_binary):
    proof = json.loads((directory / "accessibility-proof.json").read_text(encoding="utf-8"))
    sessions = proof.get("sessions", [])
    if (len(sessions) != 2 or {s.get("language") for s in sessions} != {"de", "en"}
            or any(s.get("native_elf_sha256") != expected_binary for s in sessions)
            or proof.get("complete_product_acceptance") is not False):
        raise ValueError("Actual slide switch executable/language evidence missing")
    for language in ["de", "en"]:
        captions = None
        for mode in ["on", "off"]:
            stem = directory / f"accessibility-{language}-switches-{mode}"
            rows = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
            controls = [r for r in rows
                        if r.get("role") in {"check box", "switch", "toggle button"}]
            names = {r.get("name") for r in controls}
            if len(controls) != 2 or len(names) != 2 or any(not n for n in names):
                raise ValueError("Two distinct named native switches required")
            if captions is not None and names != captions:
                raise ValueError("Different controls were captured in on/off states")
            captions = names
            for control in controls:
                checked = any("STATE_CHECKED" in s for s in control.get("states", []))
                if checked != (mode == "on"):
                    raise ValueError("Actual accessible switch state differs from screenshot mode")
            geometry = json.loads(stem.with_name(stem.name + "-geometry.json")
                                  .read_text(encoding="utf-8"))
            if len(geometry) != 2 or {g.get("name") for g in geometry} != names:
                raise ValueError("Actual switch geometry/caption binding missing")
            with Image.open(stem.with_suffix(".png")) as source:
                image = source.convert("RGB")
                for item in geometry:
                    x, y, w, h = [item.get(k) for k in ["x", "y", "width", "height"]]
                    if (any(type(n) is not int for n in [x, y, w, h]) or min(x, y) < 0
                            or min(w, h) < 20 or x+w > image.width or y+h > image.height):
                        raise ValueError("Actual switch is clipped or has invalid bounds")
                    green = sum(g > r+30 and g > b+20 for r, g, b
                                in image.crop((x, y, x+w, y+h)).getdata())
                    if (mode == "on" and green < 80) or (mode == "off" and green > 10):
                        raise ValueError("Switch pixels do not show the actual on/off state")
    return proof
