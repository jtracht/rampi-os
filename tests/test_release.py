import shutil
import subprocess
import sys
from pathlib import Path


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
