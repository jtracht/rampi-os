"""Measure rendered remote-tile contours in actual compositor PNGs (no image synthesis)."""

import json
import os
from pathlib import Path

from PIL import Image

root = Path(os.environ["RAMPI_TEST_ARTIFACTS"])
geometry = json.loads((root / "interaction-geometry.json").read_text())


def mask(name, kind="tile"):
    record = geometry[name]
    image = Image.open(root / f"interaction-{name}.png").convert("RGB")
    assert image.size == (record["width"], record["height"])
    tile = record[kind]
    x, y, width, height = (round(tile[key]) for key in ["x", "y", "width", "height"])
    assert 0 <= x < x + width <= image.width and 0 <= y < y + height <= image.height
    pixels = image.load()
    return [
        [
            (8 < pixels[x + i, y + j][0] < 45
             and 60 < pixels[x + i, y + j][1] < 110
             and 110 < pixels[x + i, y + j][2] < 165)
            if kind == "control" else
            50 < pixels[x + i, y + j][0] < 145
            and 35 < pixels[x + i, y + j][1] < 125
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
    if phase == "focus":
        samples += [mask("focus-" + suffix) for suffix in "cd"]
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
tile = geometry["reduced-a"]["tile"]
image = Image.open(root / "interaction-reduced-a.png").convert("RGB")
x, y, width, height = (round(tile[key]) for key in ["x", "y", "width", "height"])
for dx, dy in [(8, 8), (width - 9, 8), (8, height - 9), (width - 9, height - 9)]:
    assert image.getpixel((x + dx, y + dy)) == (8, 15, 22), (
        "Dashboard tile acquired an extra button skin/focus frame"
    )
first = mask("control-a", "control")
samples = [mask("control-" + suffix, "control") for suffix in "bcd"]
height, width = len(first), len(first[0])
regions = {
    "top": (range(20, width - 20), range(0, 10)),
    "bottom": (range(20, width - 20), range(height - 10, height)),
    "left": (range(0, 10), range(20, height - 20)),
    "right": (range(width - 10, width), range(20, height - 20)),
}
changes = {
    edge: max(sum(first[y][x] != second[y][x] for x in xs for y in ys) for second in samples)
    for edge, (xs, ys) in regions.items()
}
assert all(count >= 1 for count in changes.values()), ("native-control", changes)
assert len(set(changes.values())) > 1, ("native-control", changes)
assert mask("control-reduced-a", "control") == mask("control-reduced-b", "control")
assert mask("control-system-reduced-a", "control") == mask("control-system-reduced-b", "control")
evidence["native-control"] = changes
assert not any(any(row) for row in mask("category-pointer-keyboard", "control")), (
    "Stationary hidden pointer left a second active category after keyboard navigation"
)
assert geometry["dashboard-1600"]["width"] == 1600
assert geometry["dashboard-1920"]["width"] == 1920
assert geometry["dashboard-1920"]["height"] == 1080
for name in ["host", "wifi", "bluetooth", "system", "board"]:
    image = Image.open(root / f"interaction-settings-{name}.png")
    assert image.width >= 1280 and image.height >= 720
(root / "visual-acceptance.json").write_text(json.dumps(evidence, indent=2) + "\n")
(root / "visual-acceptance.json").chmod(0o644)
print("RAMPI_RUST_FOUR_EDGE_VISUAL_OK " + json.dumps(evidence, separators=(",", ":")))
