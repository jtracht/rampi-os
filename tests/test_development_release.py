"""Prerelease publication guard regressions; no real release or boot is simulated."""

import json
import runpy
import subprocess
from pathlib import Path

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "scripts/prepare-development-release.py"))


def test_explicit_native_prerelease_tag():
    assert MODULE["development_tag"]("0.6.0-dev.1") == "v0.6.0-dev.1"


@pytest.mark.parametrize(
    "version",
    ["0.6.0", "v0.6.0-dev.1", "0.6.0-dev.01", "0.6.0-dev.1/other", "0.6.0-dev.1\n", "01.6.0-dev.1"],
)
def test_reject_regular_or_unsafe_tag(version):
    with pytest.raises(ValueError):
        MODULE["development_tag"](version)


@pytest.mark.parametrize(
    "status,stdout", [(0, "a" * 40 + " refs/tags/v0.6.0-dev.1"), (128, ""), (2, "unexpected")]
)
def test_existing_or_unverifiable_tag_cannot_be_replaced(tmp_path, monkeypatch, status, stdout):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, status, stdout, "")
    )
    with pytest.raises(ValueError):
        MODULE["check_remote_tag"](tmp_path, "v0.6.0-dev.1")


def test_verified_absent_remote_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 2, "", "")
    )
    MODULE["check_remote_tag"](tmp_path, "v0.6.0-dev.1")


def test_regular_readiness_cannot_be_published_as_unfinished_development(tmp_path):
    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging/readiness.json").write_text(json.dumps({"regular_release": True}))
    with pytest.raises(ValueError, match="specifically"):
        MODULE["assemble"](tmp_path, tmp_path / "missing-image", "0.6.0-dev.1", "a" * 40)


def test_mismatching_image_readiness_rejected_before_publication(tmp_path):
    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging/readiness.json").write_text(json.dumps({"regular_release": False}))
    image = tmp_path / "image"
    image.mkdir()
    (image / "readiness.json").write_text(json.dumps({"regular_release": True}))
    with pytest.raises(ValueError, match="readiness"):
        MODULE["assemble"](tmp_path, image, "0.6.0-dev.1", "a" * 40)


def test_symlink_is_not_a_release_asset(tmp_path):
    target = tmp_path / "target"
    target.write_text("public test fixture")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation unavailable on this test account")
    with pytest.raises(ValueError, match="regular"):
        MODULE["regular_file"](link)
