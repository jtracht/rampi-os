"""Publication auditing must reject mismatched source and stability before downloading."""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("draft,prerelease", [(True, False), (False, True)])
def test_stable_audit_rejects_unpublished_or_prerelease(tmp_path, monkeypatch, draft, prerelease):
    script = runpy.run_path(str(ROOT / "scripts/verify-published-native-release.py"))
    audit = script["audit"]
    source = tmp_path / "source"
    source.mkdir()
    (source / "Cargo.toml").write_text('[workspace.package]\nversion = "0.6.0"\n')
    monkeypatch.setitem(audit.__globals__, "ROOT", source)
    monkeypatch.setattr(script["subprocess"], "check_output", lambda *a, **kw: "a" * 40)
    monkeypatch.setattr(script["subprocess"], "run", lambda *a, **kw: None)
    calls = []

    def api(endpoint):
        calls.append(endpoint)
        return {"tag_name": "v0.6.0", "draft": draft, "prerelease": prerelease}

    monkeypatch.setitem(audit.__globals__, "api", api)
    destination = tmp_path / "download"
    with pytest.raises(ValueError, match="stability status"):
        audit("v0.6.0", "a" * 40, destination)
    assert calls == ["releases/tags/v0.6.0"]
    assert not destination.exists()


def test_audit_rejects_other_source_before_network(tmp_path, monkeypatch):
    script = runpy.run_path(str(ROOT / "scripts/verify-published-native-release.py"))
    monkeypatch.setattr(script["subprocess"], "check_output", lambda *a, **kw: "b" * 40)
    with pytest.raises(ValueError, match="frozen validators"):
        script["audit"]("v0.6.0", "a" * 40, tmp_path / "download")
