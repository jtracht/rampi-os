import base64
import json
import os

import pytest
from rampi.config import Host, Settings, atomic_json, safe_url
from rampi.kanban import Board, Card, from_json, github, load_board
from rampi.launch import ps_literal, rdp_args, ssh_args


def test_settings_atomic_roundtrip_and_private_permissions(tmp_path):
    path = tmp_path / "personal" / "settings.json"
    settings = Settings(hosts=[Host(address="host.example", username="alice")])
    settings.save(path)
    assert Settings.load(path) == settings
    assert not list(path.parent.glob(".rampi-*"))
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "file:///etc/passwd",
        "https://user:secret@example.com",  # pragma: allowlist secret (synthetic rejection fixture)
        "javascript:alert(1)",
    ],
)
def test_url_rejects_unsafe_schemes_and_embedded_secrets(url):
    with pytest.raises(ValueError):
        safe_url(url)


@pytest.mark.parametrize("address", ["-oProxyCommand=evil", "host;id", "$(whoami)", "", "host\n"])
def test_host_rejects_options_and_shell_input(address):
    with pytest.raises(ValueError):
        Host(address=address, username="alice").validate()


def test_windows_project_is_encoded_as_literal_not_executable():
    project = "C:\\Projects\\O'Brien; $(whoami)"
    args = ssh_args(Host(address="host", username="alice", project=project), "codex")
    decoded = base64.b64decode(args[-1]).decode("utf-16le")
    assert "'C:\\Projects\\O''Brien; $(whoami)'" in decoded
    assert "StrictHostKeyChecking=yes" in args
    assert project not in args
    assert ps_literal("'a") == "'''a'"


def test_arbitrary_ai_commands_are_rejected():
    with pytest.raises(ValueError):
        ssh_args(Host(address="host", username="alice"), "powershell; rm")


def test_rdp_never_disables_certificate_verification_or_embeds_password(monkeypatch):
    monkeypatch.setattr("rampi.launch.executable", lambda *names: "xfreerdp3")
    args = rdp_args(Host(address="host", username="alice"))
    assert "/cert:tofu" in args
    assert "-grab-keyboard" in args
    assert not any(a.startswith("/p:") or a == "/cert:ignore" for a in args)


def test_board_search_and_unknown_columns():
    board = Board(
        cards=[Card("1", "VPN", "Blocked", "Routing", "high", "infra"), Card("2", "UI", "Offen")]
    )
    result = board.view("routing")
    assert result["count"] == 1
    assert result["columns"][-1]["name"] == "Blocked"
    assert result["columns"][-1]["cards"][0]["id"] == "1"


def test_json_connector_and_offline_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    source = tmp_path / "board.json"
    source.write_text(json.dumps({"title": "My tasks", "cards": [{"title": "Real task"}]}))
    board = load_board("json", str(source))
    assert board.cards[0].title == "Real task"
    assert not board.cached
    source.unlink()
    cached = load_board("json", str(source))
    assert cached.cached and "Offline" in cached.warning
    assert cached.cards == board.cards


def test_cache_is_separated_by_credential_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    source = tmp_path / "board.json"
    atomic_json(source, {"cards": [{"title": "Alice only"}]})
    load_board("json", str(source), "alice")
    source.unlink()
    with pytest.raises(OSError):
        load_board("json", str(source), "bob")


def test_invalid_json_never_silently_becomes_demo_data():
    with pytest.raises(ValueError):
        from_json({"cards": [{"description": "Missing title"}]})


def test_github_pagination_is_read_only_and_preserves_status(monkeypatch):
    calls = []

    def api(url, token, body):
        from graphql import parse

        parse(body["query"])
        calls.append(body)
        page = len(calls)
        return {
            "data": {
                "organization": {
                    "projectV2": {
                        "title": "Live Project",
                        "items": {
                            "pageInfo": {"hasNextPage": page == 1, "endCursor": "cursor"},
                            "nodes": [
                                {
                                    "id": str(page),
                                    "content": {"title": f"Task {page}", "body": "Details"},
                                    "fieldValues": {
                                        "nodes": [{"field": {"name": "Status"}, "name": "Review"}]
                                    },
                                }
                            ],
                        },
                    }
                }
            }
        }

    monkeypatch.setattr("rampi.kanban.request", api)
    board = github("organization/example/1", "test-fixture")
    assert len(board.cards) == 2
    assert board.cards[1].status == "Review"
    assert calls[1]["variables"]["after"] == "cursor"
    assert all("mutation" not in call["query"] for call in calls)


def test_invalid_configuration_is_preserved_for_repair(tmp_path):
    path = tmp_path / "settings.json"
    original = '{"unexpected": true}'
    path.write_text(original)
    with pytest.raises(ValueError):
        Settings.load(path)
    assert path.read_text() == original


def test_api_redirect_does_not_forward_tokens(monkeypatch):
    from rampi.kanban import request

    def opener(handler):
        with pytest.raises(ValueError):
            handler().redirect_request(None, None, 302, "", {}, "https://attacker.invalid")
        raise RuntimeError("test complete")

    monkeypatch.setattr("urllib.request.build_opener", opener)
    with pytest.raises(RuntimeError, match="test complete"):
        request("https://api.github.com", "sensitive-fixture")


@pytest.mark.parametrize("name", ["-root", "Root", "name;cmd", "user\n", "a" * 32])
def test_account_validation_rejects_unsafe_names(name):
    from rampi.accounts import validate_new_user

    with pytest.raises(ValueError):
        validate_new_user(name, "synthetic-test-only")
