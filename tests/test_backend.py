import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402


def test_failed_save_does_not_change_active_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings())
    backend.timer.stop()
    assert not backend.save({"address": "-bad", "username": "alice"})
    assert backend.settings.hosts == []
    assert not (tmp_path / "rampi" / "settings.json").exists()
    assert app is not None


def test_save_retains_other_hosts(tmp_path, monkeypatch):
    from rampi.config import Host

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    initial = Settings(hosts=[Host(address="one", username="a"), Host(address="two", username="b")])
    backend = Backend(initial)
    backend.timer.stop()
    assert backend.save({"address": "changed", "username": "a"})
    assert backend.settings.hosts[1].address == "two"
    assert Settings.load().hosts[0].address == "changed"
    backend.jobs.pool.waitForDone()
    assert app is not None
