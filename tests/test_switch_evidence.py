"""Pixel/check-state verifier controls; fixtures are not real UI acceptance."""

import json
import runpy
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

check = runpy.run_path(str(Path(__file__).resolve().parents[1]
                          / "scripts/check-switch-evidence.py"))["check"]


@pytest.fixture
def captures(tmp_path):
    proof = {"sessions": [{"language": lang, "native_elf_sha256": "a" * 64}
                          for lang in ["de", "en"]], "complete_product_acceptance": False}
    (tmp_path / "accessibility-proof.json").write_text(json.dumps(proof))
    for language in ["de", "en"]:
        for mode in ["on", "off"]:
            stem = tmp_path / f"accessibility-{language}-switches-{mode}"
            rows = [{"role": "check box", "name": name,
                     "states": ["STATE_CHECKED"] if mode == "on" else []}
                    for name in ["Motion", "Sound"]]
            stem.with_suffix(".json").write_text(json.dumps(rows))
            boxes = [{"name": name, "x": x, "y": 10, "width": 30, "height": 30}
                     for name, x in [("Motion", 10), ("Sound", 60)]]
            stem.with_name(stem.name + "-geometry.json").write_text(json.dumps(boxes))
            image = Image.new("RGB", (120, 60), "#080f16")
            paint = ImageDraw.Draw(image)
            for box in boxes:
                paint.rectangle((box["x"], 10, box["x"] + 29, 39),
                                fill="#13855a" if mode == "on" else "#425462")
            image.save(stem.with_suffix(".png"))
    return tmp_path


def test_accept_matching_state_geometry_and_pixels(captures):
    check(captures, "a" * 64)


def test_reject_different_program(captures):
    with pytest.raises(ValueError, match="executable"):
        check(captures, "b" * 64)


def test_reject_green_off_screenshot(captures):
    source = captures / "accessibility-de-switches-on.png"
    (captures / "accessibility-de-switches-off.png").write_bytes(source.read_bytes())
    with pytest.raises(ValueError, match="pixels"):
        check(captures, "a" * 64)


def test_reject_checked_flag_in_off_capture(captures):
    path = captures / "accessibility-de-switches-off.json"
    data = json.loads(path.read_text())
    data[0]["states"] = ["STATE_CHECKED"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="accessible switch state"):
        check(captures, "a" * 64)


def test_reject_clipped_geometry(captures):
    path = captures / "accessibility-de-switches-on-geometry.json"
    data = json.loads(path.read_text())
    data[0]["x"] = 110
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="clipped"):
        check(captures, "a" * 64)
