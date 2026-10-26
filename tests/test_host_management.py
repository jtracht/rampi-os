from PySide6.QtCore import QCoreApplication
from rampi.backend import Backend
from rampi.config import Host, Settings


def backend_for(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings(hosts=[Host(name="One", address="one", username="alice")]))
    backend.timer.stop()
    assert app is not None
    return backend


def test_profiles_create_select_edit_remove_and_persist(tmp_path, monkeypatch):
    backend = backend_for(tmp_path, monkeypatch)
    assert backend.saveHost({"name": "Two", "address": "two", "username": "bob"}, -1)
    assert backend.settings.host.address == "one"
    assert backend.selectHost(1)
    assert backend.saveHost({"project": "C:\\New project", "resolution": "1920x1080"}, 1)
    assert backend.settings.host.project == "C:\\New project"
    assert backend.settings.host.resolution == "1920x1080"
    assert backend.removeHost(0)
    assert backend.settings.active_host == 0
    assert Settings.load().host.username == "bob"
    assert backend.removeHost(0)
    assert Settings.load().hosts == []


def test_invalid_profile_never_changes_saved_configuration(tmp_path, monkeypatch):
    backend = backend_for(tmp_path, monkeypatch)
    backend.settings.save()
    before = Settings.load()
    assert not backend.saveHost({"address": "-bad"}, 0)
    assert not backend.selectHost(-1)
    assert not backend.removeHost(5)
    assert Settings.load() == before


def test_live_clients_block_target_changes_without_writing_settings(tmp_path, monkeypatch):
    backend = backend_for(tmp_path, monkeypatch)
    assert backend.saveHost({"address": "two", "username": "bob"}, -1)

    class Connected:
        def poll(self):
            return None

    backend.children_processes["rdp"] = Connected()
    assert not backend.selectHost(1)
    assert not backend.save({"address": "changed", "username": "alice"})
    assert not backend.removeHost(0)
    assert Settings.load().host.address == "one"
