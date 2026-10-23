"""Measure rendered blue-tile contours in actual compositor PNGs (no image synthesis)."""

import json
import os
from pathlib import Path

from PIL import Image

root = Path(os.environ["RAMPI_TEST_ARTIFACTS"])
geometry = json.loads((root / "interaction-geometry.json").read_text())


def mask(name):
    record = geometry[name]
    image = Image.open(root / f"interaction-{name}.png").convert("RGB")
    assert image.size == (record["width"], record["height"])
    tile = record["tile"]
    x, y, width, height = (round(tile[key]) for key in ["x", "y", "width", "height"])
    assert 0 <= x < x + width <= image.width and 0 <= y < y + height <= image.height
    pixels = image.load()
    return [
        [
            pixels[x + i, y + j][0] < 40
            and 90 < pixels[x + i, y + j][1] < 180
            and pixels[x + i, y + j][2] > 180
            for i in range(width)
        ]
        for j in range(height)
    ]


evidence = {}
for phase in ["startup", "hover", "focus"]:
    first = mask(phase + "-a")
    samples = [mask(phase + "-b")]
    if phase == "startup":
        samples += [mask("startup-" + suffix) for suffix in "cdef"]
    height, width = len(first), len(first[0])
    regions = {
        "top": (range(40, width - 40), range(0, 30)),
        "bottom": (range(40, width - 40), range(height - 30, height)),
        "left": (range(0, 30), range(40, height - 40)),
        "right": (range(width - 30, width), range(40, height - 40)),
    }
    changes = {
        edge: max(sum(first[y][x] != second[y][x] for x in xs for y in ys) for second in samples)
        for edge, (xs, ys) in regions.items()
    }
    assert all(count >= 4 for count in changes.values()), (phase, changes)
    # Independent edge movement must not collapse into a rectangular translation.
    assert len(set(changes.values())) > 1, (phase, changes)
    evidence[phase] = changes

assert mask("reduced-a") == mask("reduced-b"), "Reduced motion still moves the rendered contour"
assert geometry["dashboard-1600"]["width"] == 1600
for name in ["host", "wifi", "bluetooth", "system", "board"]:
    image = Image.open(root / f"interaction-settings-{name}.png")
    assert image.width >= 1280 and image.height >= 720
(root / "visual-acceptance.json").write_text(json.dumps(evidence, indent=2) + "\n")
print("RAMPI_RUST_FOUR_EDGE_VISUAL_OK " + json.dumps(evidence, separators=(",", ":")))
