"""Synthetic checker guards only; actual server acceptance is a separate Docker run."""

import copy
import json
import runpy
import struct
from pathlib import Path

import pytest

CHECK = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check-gitea-evidence.py"))["check"]


@pytest.fixture
def evidence(tmp_path):
    report = {
        "image": "docker.gitea.com/gitea:28.2.0@sha256:"
        # pragma: allowlist nextline secret - public official Gitea image SHA256
        "30777c91280d973fa02be48b1ade735bd6859e8f6f7af3b4444d519437852504",
        "version": "gitea version 28.2.0 fixture",
        "private_network": True,
        "published_ports": False,
        "read_only_write_denied_http": 403,
        "page_size": 1,
        "cards": 2,
        "refresh": True,
        "offline": True,
        "actual_server_issues": [
            {"id": 1, "title": "Rampi first updated"},
            {"id": 2, "title": "Rampi second"},
        ],
        "binary_sha256": "b" * 64,
    }
    (tmp_path / "gitea-environment.json").write_text(json.dumps(report))
    (tmp_path / "gitea-program-sha256.txt").write_text("b" * 64)
    (tmp_path / "gitea-live.log").write_text("RAMPI_RUST_GITEA_LIVE_PAGE_OK")
    (tmp_path / "gitea-live.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + bytes(8) + struct.pack(">II", 1280, 720)
    )
    for name in ("refresh", "offline"):
        for suffix in ("ready", "continue"):
            (tmp_path / f"gitea-{name}-{suffix}").write_text(name)
    return tmp_path, report


def test_complete_synthetic_guard_input(evidence):
    folder, report = evidence
    assert CHECK(folder) == report


@pytest.mark.parametrize(
    "field,value",
    [
        ("image", "unverified:latest"),
        ("published_ports", True),
        ("read_only_write_denied_http", 201),
        ("page_size", 100),
        ("binary_sha256", "c" * 64),
        ("actual_server_issues", []),
    ],
)
def test_incomplete_or_wrong_scope_rejected(evidence, field, value):
    folder, original = evidence
    changed = copy.deepcopy(original)
    changed[field] = value
    (folder / "gitea-environment.json").write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        CHECK(folder)


@pytest.mark.parametrize(
    "filename",
    ["gitea-live.log", "gitea-live.png", "gitea-offline-continue", "gitea-refresh-ready"],
)
def test_missing_runtime_output_rejected(evidence, filename):
    folder, _ = evidence
    (folder / filename).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        CHECK(folder)
