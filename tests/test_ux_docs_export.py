"""Exporter integrity tests; generated test PNGs are never published UI evidence."""

import hashlib
import json
import runpy
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / "scripts/export-ux-docs.py"


@pytest.fixture
def exporter(tmp_path, monkeypatch):
    scope = runpy.run_path(str(MODULE))
    export = scope["export"]
    checked = []

    def validator(path):
        return {"check": lambda *args: checked.append(Path(path).name)}

    # These tests target copying/atomicity. Real capture validators have their
    # own negative tests and are mandatory in the actual native CI exporter.
    monkeypatch.setitem(export.__globals__, "runpy", SimpleNamespace(run_path=validator))
    captures = tmp_path / "captures"
    captures.mkdir()
    for _, name, _ in scope["CAPTURES"]:
        Image.new("RGB", (400, 240), "#123456").save(captures / name)
    return export, captures, tmp_path / "docs", checked


def test_copy_preserves_every_byte_and_zip_contains_gallery(exporter):
    export, captures, output, checked = exporter
    proof = export(captures, output, "a" * 64)
    assert len(checked) == 3
    assert proof["images_modified"] is False
    assert proof["complete_product_acceptance"] is False
    with zipfile.ZipFile(str(output) + ".zip") as archive:
        assert {"README.md", "manifest.json"} <= set(archive.namelist())
        for record in proof["screenshots"]:
            assert hashlib.sha256(archive.read(record["file"])).hexdigest() == record["sha256"]
    for record in proof["screenshots"]:
        assert (output / record["file"]).is_file()


def test_existing_directory_is_preserved(exporter):
    export, captures, output, _ = exporter
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("Keep existing work")
    with pytest.raises(FileExistsError):
        export(captures, output, "a" * 64)
    assert sentinel.read_text() == "Keep existing work"


def test_existing_archive_with_dotted_destination_is_preserved(exporter):
    export, captures, output, _ = exporter
    output = output.with_name("docs.dev7")
    archive = Path(str(output) + ".zip")
    archive.write_bytes(b"Keep existing archive")
    with pytest.raises(FileExistsError):
        export(captures, output, "a" * 64)
    assert archive.read_bytes() == b"Keep existing archive"


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_incomplete_capture_never_creates_partial_gallery(exporter, damage):
    export, captures, output, _ = exporter
    source = captures / "accessibility-de-dashboard.png"
    if damage == "missing":
        source.unlink()
    else:
        source.write_bytes(b"Not an actual captured PNG")
    with pytest.raises((FileNotFoundError, OSError)):
        export(captures, output, "a" * 64)
    assert not output.exists()


def test_mismatched_rdp_program_is_rejected(exporter, tmp_path):
    export, captures, output, _ = exporter
    remote = tmp_path / "remote"
    remote.mkdir()
    (remote / "rdp-input.json").write_text(json.dumps({"native_elf_sha256": "b" * 64}))
    with pytest.raises(ValueError, match="another or unrecorded"):
        export(captures, output, "a" * 64, rdp=remote)
    assert not output.exists()


def test_failed_capture_validation_prevents_all_exports(exporter, monkeypatch):
    export, captures, output, _ = exporter

    def reject(*_):
        raise ValueError("Wrong actual executable")

    monkeypatch.setitem(export.__globals__, "runpy", SimpleNamespace(
        run_path=lambda _: {"check": reject}))
    with pytest.raises(ValueError, match="Wrong actual executable"):
        export(captures, output, "a" * 64)
    assert not output.exists()
