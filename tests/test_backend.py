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


def test_streaming_requires_pairing_for_the_selected_account(tmp_path, monkeypatch):
    from rampi.config import Host

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings(hosts=[Host(address="workstation", username="alice")]))
    backend.timer.stop()
    messages = []
    backend.message.connect(messages.append)
    launched = []
    monkeypatch.setattr(backend, "_launch", lambda *args: launched.append(args))
    backend.launch("stream")
    assert not launched
    assert "Streaming-Host koppeln" in messages[-1]
    assert app is not None


def test_old_board_response_and_error_cannot_replace_new_source(tmp_path, monkeypatch):
    from rampi.kanban import Board, Card

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings(board_source="old.json"))
    backend.timer.stop()
    old = backend._board_generation
    assert backend.save({"board_source": "new.json"})
    messages = []
    backend.message.connect(messages.append)
    backend._result(f"board-{old}", Board(cards=[Card("private", "Previous project")]))
    backend._failed(f"board-{old}", "Outdated source failed")
    assert backend.board["total"] == 0 and not messages
    backend._result(f"board-{backend._board_generation}", Board(cards=[Card("new", "Current")]))
    assert backend.board["count"] == 1
    backend.jobs.pool.waitForDone()
    assert app is not None


def test_disappearing_filter_choice_resets_without_hiding_all_cards(tmp_path, monkeypatch):
    from rampi.kanban import Board, Card

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings())
    backend.timer.stop()
    backend._result("board-0", Board(cards=[Card("1", "Task", project="Old")]))
    backend.filterBoard("Old", "", "")
    backend._result("board-0", Board(cards=[Card("2", "Other", project="New")]))
    assert backend.board["count"] == 1 and backend.board["filters"]["project"] == ""
    assert app is not None


def test_old_vpn_snapshot_and_error_cannot_replace_current_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings())
    backend.timer.stop()
    backend._vpn_generation = 2
    current = [{"uuid": "current", "name": "Personal", "active": True}]
    backend._result("vpn-profiles-2", current)
    backend._result("vpn-profiles-1", [{"uuid": "old", "active": False}])
    backend._failed("vpn-profiles-1", "Outdated error")
    assert backend.vpnProfiles["profiles"] == current
    assert backend.vpnProfiles["error"] == ""
    assert app is not None


def test_competing_wireguard_action_is_not_started(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = Backend(Settings())
    backend.timer.stop()
    backend.jobs.pending.add("wg-up")
    messages = []
    backend.message.connect(messages.append)
    backend.action("wg-down", "00000000-0000-0000-0000-000000000000")
    assert backend.jobs.pending == {"wg-up"}
    assert backend.vpnProfiles["busy"] and "bereits" in messages[-1]
    backend.jobs.pending.clear()
    assert app is not None
