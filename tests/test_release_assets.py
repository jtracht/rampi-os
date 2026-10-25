"""Real file/byte transport and corruption guards for oversized release sources."""

import hashlib
import io
import json
import runpy
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts/release-assets.py"))
SOURCE = MODULE["SOURCE"]
INDEX = MODULE["INDEX"]


def fixture(directory, payload=bytes(range(256)) * 3):
    (directory / SOURCE).write_bytes(payload)
    assert MODULE["split_sources"](directory, threshold=256, part_bytes=200)
    return payload


def test_byte_exact_multifile_restore_and_exclusive_destination(tmp_path):
    payload = fixture(tmp_path)
    assert not (tmp_path / SOURCE).exists()
    index = MODULE["parts"](tmp_path)
    assert index["size"] == len(payload)
    assert index["sha256"] == hashlib.sha256(payload).hexdigest()
    assert all(item["size"] <= 200 for item in index["parts"])
    output = tmp_path / "restored.tar.xz"
    MODULE["restore"](tmp_path, output)
    assert output.read_bytes() == payload
    with pytest.raises(FileExistsError):
        MODULE["restore"](tmp_path, output)
    assert output.read_bytes() == payload


def test_small_archive_is_preserved_and_exact_limit_is_split(tmp_path):
    source = tmp_path / SOURCE
    source.write_bytes(b"a" * 255)
    assert not MODULE["split_sources"](tmp_path, threshold=256, part_bytes=128)
    assert source.read_bytes() == b"a" * 255
    source.write_bytes(b"a" * 256)
    assert MODULE["split_sources"](tmp_path, threshold=256, part_bytes=128)
    assert [item["size"] for item in MODULE["parts"](tmp_path)["parts"]] == [128, 128]


@pytest.mark.parametrize("change", ["corrupt", "missing", "reorder", "unsafe", "whole-hash"])
def test_corrupt_incomplete_unsafe_or_reordered_sources_rejected(tmp_path, change):
    fixture(tmp_path)
    index = json.loads((tmp_path / INDEX).read_text())
    first = tmp_path / index["parts"][0]["name"]
    if change == "corrupt":
        first.write_bytes(b"x" * first.stat().st_size)
    elif change == "missing":
        first.unlink()
    elif change == "reorder":
        index["parts"].reverse()
    elif change == "unsafe":
        index["parts"][0]["name"] = "../escape"
    else:
        index["sha256"] = "0" * 64
    (tmp_path / INDEX).write_text(json.dumps(index))
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        MODULE["restore"](tmp_path, output)
    assert not output.exists()


def test_existing_parts_are_not_overwritten(tmp_path):
    source = tmp_path / SOURCE
    source.write_bytes(b"original" * 100)
    part = tmp_path / (SOURCE + ".part001")
    part.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="overwrite"):
        MODULE["split_sources"](tmp_path, threshold=256, part_bytes=200)
    assert source.read_bytes() == b"original" * 100
    assert part.read_bytes() == b"preserve"


def test_upload_limit_is_strict(tmp_path, monkeypatch):
    monkeypatch.setitem(MODULE["check_limits"].__globals__, "LIMIT", 256)
    source = tmp_path / "asset"
    source.write_bytes(b"a" * 255)
    MODULE["check_limits"](tmp_path)
    source.write_bytes(b"a" * 256)
    with pytest.raises(ValueError, match="per-file"):
        MODULE["check_limits"](tmp_path)


def test_complete_source_inventory_survives_transport(tmp_path):
    source = tmp_path / SOURCE
    with tarfile.open(source, "w:xz") as archive:
        for name, data in [
            ("files/example.orig.tar.gz", bytes(range(256)) * 4),
            ("files/example.dsc", b"Source: example\nVersion: 1\n"),
        ]:
            info = tarfile.TarInfo("opt/rampi-corresponding-sources/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    inventory = runpy.run_path(str(ROOT / "scripts/check-source-archives.py"))["inventory"]
    before = inventory(source, "opt/rampi-corresponding-sources")
    MODULE["split_sources"](tmp_path, threshold=128, part_bytes=64)
    with MODULE["source_archive"](tmp_path) as restored:
        assert inventory(restored, "opt/rampi-corresponding-sources") == before
