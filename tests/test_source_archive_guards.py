"""Synthetic archive guard fixtures, not image or upstream-source acceptance."""

import copy
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "source_archives", Path(__file__).resolve().parents[1] / "scripts/check-source-archives.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REVISION = "a" * 40


def entry(data):
    return {"data": data, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


@pytest.fixture
def rust_sources():
    lock = (
        '[[package]]\nname="demo"\nversion="1.0.0"\n'
        'source="registry+https://example.test/index"\nchecksum="' + "a" * 64 + '"\n'
    ).encode()
    file = entry(b"source contents")
    prefix = "vendor-sources/demo-1.0.0/"
    return lock, {
        "Cargo.lock": entry(lock),
        "source-revision.txt": entry(REVISION.encode()),
        "config.toml": entry(
            b'[source.crates-io]\nreplace-with="vendored-sources"\n'
            b'[source.vendored-sources]\ndirectory="vendor-sources"\n'
        ),
        "git-source-revisions.json": entry(b"[]"),
        prefix + "src/lib.rs": file,
        prefix + ".cargo-checksum.json": entry(
            json.dumps(
                {
                    "package": "a" * 64,
                    "files": {"src/lib.rs": file["sha256"]},
                }
            ).encode()
        ),
    }


def test_exact_rust_fixture(rust_sources):
    lock, entries = rust_sources
    assert MODULE.check_rust(entries, lock, REVISION) == 1


@pytest.mark.parametrize("mutation", ["source", "revision", "lock", "extra", "missing", "config"])
def test_reject_incomplete_or_wrong_rust_sources(rust_sources, mutation):
    lock, original = rust_sources
    entries = copy.deepcopy(original)
    if mutation == "source":
        entries["vendor-sources/demo-1.0.0/src/lib.rs"] = entry(b"changed")
    elif mutation == "revision":
        entries["source-revision.txt"] = entry(b"b" * 40)
    elif mutation == "lock":
        entries["Cargo.lock"] = entry(b"different")
    elif mutation == "extra":
        entries["unverified-file"] = entry(b"unexpected")
    elif mutation == "missing":
        del entries["vendor-sources/demo-1.0.0/src/lib.rs"]
    elif mutation == "config":
        entries["config.toml"] = entry(
            entries["config.toml"]["data"].replace(
                b'directory="vendor-sources"', b'directory="/build/private-path"'
            )
        )
    with pytest.raises((ValueError, KeyError)):
        MODULE.check_rust(entries, lock, REVISION)


@pytest.mark.parametrize(
    "name,kind",
    [
        ("root/../escape", "file"),
        ("root/..\\escape", "file"),
        ("other/file", "file"),
        ("root/link", "link"),
    ],
)
def test_reject_unsafe_archive_member(tmp_path, name, kind):
    archive = tmp_path / "source.tar.xz"
    with tarfile.open(archive, "w:xz") as bundle:
        member = tarfile.TarInfo(name)
        if kind == "link":
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            bundle.addfile(member)
        else:
            member.size = 1
            bundle.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        MODULE.inventory(archive, "root")


@pytest.mark.parametrize("mutation", [None, "missing", "version", "checksum"])
def test_descriptor_requires_all_corresponding_archives(mutation):
    source = entry(b"source")
    descriptor = entry(
        (
            "Source: demo\nVersion: 1.0\nChecksums-Sha256:\n "
            + source["sha256"]
            + " 6 demo.orig.tar.xz\n"
        ).encode()
    )
    package = {
        "package": "demo",
        "version": "1.0",
        "files": [
            {"name": "demo.dsc", "sha256": descriptor["sha256"], "size": descriptor["size"]},
            {"name": "demo.orig.tar.xz", "sha256": source["sha256"], "size": source["size"]},
        ],
    }
    if mutation == "missing":
        package["files"].pop()
    elif mutation == "version":
        package["version"] = "2.0"
    elif mutation == "checksum":
        package["files"][1]["sha256"] = "b" * 64
    entries = {"files/demo.dsc": descriptor, "files/demo.orig.tar.xz": source}
    if mutation is None:
        MODULE.check_descriptor(package, entries)
    else:
        with pytest.raises(ValueError):
            MODULE.check_descriptor(package, entries)


def test_reject_git_source_with_different_commit(rust_sources):
    original_lock, entries = rust_sources
    source = "git+https://example.test/source?rev=" + REVISION + "#" + REVISION
    lock = original_lock.replace(b"registry+https://example.test/index", source.encode())
    lock = lock.replace(('checksum="' + "a" * 64 + '"\n').encode(), b"")
    entries["Cargo.lock"] = entry(lock)
    entries["config.toml"] = entry(
        entries["config.toml"]["data"]
        + ('\n[source."' + source.split("#")[0] + '"]\nreplace-with="vendored-sources"\n').encode()
    )
    checksums = json.loads(entries["vendor-sources/demo-1.0.0/.cargo-checksum.json"]["data"])
    checksums["package"] = None
    entries["vendor-sources/demo-1.0.0/.cargo-checksum.json"] = entry(
        json.dumps(checksums).encode()
    )
    entries["git-source-revisions.json"] = entry(
        json.dumps(
            [
                {"name": "demo", "version": "1.0.0", "source": source, "commit": "b" * 40},
            ]
        ).encode()
    )
    with pytest.raises(ValueError, match="locked commit"):
        MODULE.check_rust(entries, lock, REVISION)
