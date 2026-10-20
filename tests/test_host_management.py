import base64
import json

from PySide6.QtCore import QCoreApplication
from rampi.backend import Backend
from rampi.config import Host, Settings
from rampi.launch import session_args


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

    backend.children_processes["codex"] = Connected()
    assert not backend.selectHost(1)
    assert not backend.save({"address": "changed", "username": "alice"})
    assert not backend.removeHost(0)
    assert Settings.load().host.address == "one"


def test_old_host_responses_cannot_populate_new_host(tmp_path, monkeypatch):
    backend = backend_for(tmp_path, monkeypatch)
    old = backend._host_generation
    assert backend.saveHost({"address": "two", "username": "bob"}, -1)
    assert backend.selectHost(1)
    backend._result(f"preview-{old}-codex", "Private output from Alice")
    backend._result(f"host-key-{old}", {"fingerprints": "Alice fingerprint"})
    backend._result(
        f"session-{old}-codex", json.dumps({"schema": 1, "module": "codex", "running": True})
    )
    backend._failed(f"preview-{old}-claude", "old error")
    assert "Alice" not in str(backend.previews)
    assert backend.hostKey == {"fingerprints": ""}
    assert backend.sessions[0]["state"] == "Ungeprüft"


def test_session_status_requires_the_requested_module(tmp_path, monkeypatch):
    backend = backend_for(tmp_path, monkeypatch)
    generation = backend._host_generation
    backend._result(f"session-{generation}-codex", '{"schema":1,"module":"codex","running":true}')
    assert backend.sessions[0]["state"] == "Läuft auf Windows"
    backend._result(f"session-{generation}-codex", '{"schema":1,"module":"claude","running":true}')
    assert backend.sessions[0]["state"] == "Windows-Adapter aktualisieren"


def test_session_commands_are_fixed_and_use_verified_noninteractive_ssh():
    import pytest

    host = Host(address="one", username="alice")
    args = session_args(host, "codex", "Stop")
    decoded = base64.b64decode(args[-1]).decode("utf-16le")
    assert "-Action 'Stop'" in decoded and "-Module 'codex'" in decoded
    assert "StrictHostKeyChecking=yes" in args and "BatchMode=yes" in args
    with pytest.raises(ValueError):
        session_args(host, "codex; whoami", "Stop")
    with pytest.raises(ValueError):
        session_args(host, "codex", "kill-server")
