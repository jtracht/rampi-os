"""Synthetic source-inventory guard cases; not upstream or image acceptance."""

import hashlib
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "moonlight_sources", Path(__file__).resolve().parents[1] / "scripts/check-source-archives.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def archive(entries, compression):
    target = io.BytesIO()
    with tarfile.open(fileobj=target, mode="w:" + compression) as tar:
        for name, data in entries.items():
            item = tarfile.TarInfo(name)
            item.size = len(data)
            tar.addfile(item, io.BytesIO(data))
    return target.getvalue()


def bundle(tmp_path, *, changed=False, missing=False, wrong_path=False):
    files = {
        "LICENSE": b"fixture license",
        "third_party/moonlight-common-c/LICENSE.txt": b"fixture",
        "third_party/moonlight-common-c/src/Connection.c": b"fixture source",
    }
    files.update({f"fixture-{index}.c": b"fixture" for index in range(7)})
    manifest = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()
    ).encode()
    if changed:
        files["third_party/moonlight-common-c/src/Connection.c"] = b"changed source"
    if missing:
        files.pop("third_party/moonlight-common-c/LICENSE.txt")
    # Public upstream source revisions, not credentials.
    revisions = (
        b"embedded=775444287305849ebdf4736c75298ad0713e2d5d\n"  # pragma: allowlist secret
        b"common=b126e481a195fdc7152d211def17190e3434bcce\n"
    )  # pragma: allowlist secret
    binary = (
        "/opt/unrelated-library" if wrong_path else "/usr/local/lib/libmoonlight-common.so.2.7.1"
    )
    entries = {
        "moonlight-source-revisions.txt": revisions,
        "moonlight-runtime.sha256": ("a" * 64 + "  " + binary + "\n").encode(),
        "moonlight-source-files.sha256": manifest,
        "moonlight-embedded-2.7.1-source.tar.gz": archive(
            {"source/" + name: data for name, data in files.items()}, "gz"
        ),
    }
    path = tmp_path / "licenses.tar.xz"
    path.write_bytes(
        archive({"dependency-licenses/" + name: data for name, data in entries.items()}, "xz")
    )
    return path


def test_complete_source_inventory_guard(tmp_path):
    MODULE.check_moonlight(bundle(tmp_path))


@pytest.mark.parametrize("option", ["changed", "missing", "wrong_path"])
def test_reject_altered_or_missing_c_sources_and_unrelated_binary(tmp_path, option):
    with pytest.raises(ValueError):
        MODULE.check_moonlight(bundle(tmp_path, **{option: True}))
