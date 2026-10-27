import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def test_release_gate_rejects_development_suffix_left_on_runtime_version(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    checker = scripts / "check-release.py"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts/check-release.py", checker)
    (tmp_path / "client/rampi").mkdir(parents=True)
    (tmp_path / "client/rampi/__init__.py").write_text('__version__ = "0.2.0.dev0"\n')
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n')
    (tmp_path / ".release-please-manifest.json").write_text('{".": "0.2.0"}')
    result = subprocess.run(
        [sys.executable, str(checker), "--configuration-only"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "Release version mismatch" in result.stderr


@pytest.mark.parametrize("native_version", ["0.6.0-dev.2", "0.5.1", "0.6.0"])
def test_regular_release_checks_the_actual_rust_workspace_version(tmp_path, native_version):
    """Synthetic readiness files exercise only the version gate, never a release proof."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    checker = scripts / "check-release.py"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts/check-release.py", checker)
    (tmp_path / "client/rampi").mkdir(parents=True)
    (tmp_path / "client/rampi/__init__.py").write_text('__version__ = "0.6.0"\n')
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.6.0"\n')
    (tmp_path / ".release-please-manifest.json").write_text('{".": "0.6.0"}')
    (tmp_path / "release-please-config.json").write_text('{"draft": true}')
    (tmp_path / "Cargo.toml").write_text(
        '[workspace.package]\nversion = "' + native_version + '"\n'
    )
    (tmp_path / "packaging").mkdir()
    (tmp_path / "fixture.txt").write_text("Version-gate fixture only\n")
    (tmp_path / "packaging/readiness.json").write_text(json.dumps({
        "schema": 1, "regular_release": True,
        "evidence": {str(index): "fixture.txt" for index in range(10)},
    }))
    result = subprocess.run(
        [sys.executable, str(checker)], capture_output=True, text=True, check=False
    )
    if native_version == "0.6.0":
        assert result.returncode == 0
    else:
        assert result.returncode != 0
        assert "native Rust version" in result.stderr
