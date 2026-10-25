"""Source redistribution guards; fixtures are not actual archive acceptance."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "debian_sources", Path(__file__).resolve().parents[1] / "scripts/collect-debian-sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def index(package="dash", version="1:2.0-1", name="dash_2.0-1.dsc", digest="a" * 64):
    return f"Package: {package}\nVersion: {version}\nChecksums-Sha256:\n {digest} 123 {name}\n"


def test_installed_binary_versions_do_not_replace_source_versions():
    assert MODULE.source_versions(
        "libexample:arm64\t1:2.0-1+b2\texample\t1:2.0-1\n"
        "example-tools\t1:2.0-1+b2\texample\t1:2.0-1\n"
    ) == [("example", "1:2.0-1")]


@pytest.mark.parametrize("manifest", ["", "malformed", "x\t1\t../x\t1", "x\t1\tx\t--bad"])
def test_reject_invalid_manifest(manifest):
    with pytest.raises(ValueError):
        MODULE.source_versions(manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("package", "different"),
        ("version", "2.1"),
        ("name", "../escape.dsc"),
        ("name", "..\\escape.dsc"),
        ("digest", "not-a-checksum"),
        ("name", "dash.tar.xz"),
    ],
)
def test_reject_wrong_or_incomplete_source_index(field, value):
    with pytest.raises(ValueError):
        MODULE.index_files(index(**{field: value}), "dash", "1:2.0-1")


def test_reject_ambiguous_source_hashes():
    with pytest.raises(ValueError, match="ambiguous"):
        MODULE.index_files(index() + "\n" + index(digest="b" * 64), "dash", "1:2.0-1")


def test_missing_source_names_exact_package_and_version():
    with pytest.raises(ValueError, match=r"missing: rpi-connect-lite=2\.14\.0"):
        MODULE.index_files("", "rpi-connect-lite", "2.14.0")


def test_disabled_and_existing_source_indexes_are_preserved():
    original = "Types: deb\nURIs: https://example.test/debian\nSigned-By: /keys/repository.gpg\n"
    assert "Types: deb-src" in MODULE.source_stanzas(original)
    assert "Signed-By: /keys/repository.gpg" in MODULE.source_stanzas(original)
    assert MODULE.source_stanzas(original + "Enabled: no\n") == ""
    assert MODULE.source_stanzas(original.replace("Types: deb", "Types: deb deb-src")) == ""


def test_failure_removes_only_own_source_config(tmp_path, monkeypatch):
    apt = tmp_path / "apt"
    directory = apt / "sources.list.d"
    directory.mkdir(parents=True)
    original = directory / "vendor.sources"
    content = "Types: deb\nURIs: https://example.test/debian\nSuites: stable\nComponents: main\n"
    original.write_text(content)
    manifest = tmp_path / "packages.tsv"
    manifest.write_text("dash\t1\tdash\t1\n")

    def fail(*args, **kwargs):
        raise RuntimeError("APT unavailable")

    monkeypatch.setattr(MODULE, "command", fail)
    output = tmp_path / "download"
    with pytest.raises(RuntimeError, match="APT unavailable"):
        MODULE.collect(manifest, output, apt, True)
    assert list(directory.iterdir()) == [original]
    assert original.read_text() == content
    assert not (output / "source-archives.json").exists()
