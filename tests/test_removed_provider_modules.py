"""Old module requests must fail without starting or deleting personal programs."""
from PySide6.QtCore import QCoreApplication
from rampi.backend import Backend
from rampi.config import Host, Settings


def test_removed_modules_cannot_start_a_process_and_preserve_old_profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = Settings(hosts=[Host(address="host.example", username="alice", project="C:\\Work")])
    settings.save()
    backend = Backend(Settings.load())
    backend.timer.stop()
    errors = []
    backend.message.connect(errors.append)

    def unexpected_start(*args, **kwargs):
        raise AssertionError("Removed provider module launched a process")

    monkeypatch.setattr(backend, "_launch", unexpected_start)
    for module in ["codex", "claude", "antigravity"]:
        backend.launch(module)
    assert errors == ["Unbekanntes Modul."] * 3
    assert Settings.load().hosts[0].project == "C:\\Work"
    assert not backend.children_processes
    assert app is not None
