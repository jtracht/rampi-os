"""Provider response contract tests; not evidence of access to live personal accounts."""

import base64
import json

import pytest
from rampi import kanban


def test_trello_preserves_columns_and_never_puts_credentials_in_url(monkeypatch):
    calls = []

    def request(url, token="", body=None, headers=None):
        calls.append((url, headers))
        if url.endswith("/lists"):
            return [{"id": "list1", "name": "Review"}]
        return [{"id": "card1", "name": "Test", "desc": "Details", "idList": "list1"}]

    monkeypatch.setattr(kanban, "request", request)
    board = kanban.trello("board1", json.dumps({"key": "test-key", "token": "test-token"}))
    assert board.cards[0].status == "Review"
    assert board.cards[0].description == "Details"
    assert all("test-token" not in url for url, _ in calls)
    assert calls[0][1]["Authorization"].startswith("OAuth ")


def test_jira_cloud_uses_basic_auth_and_decodes_document_content(monkeypatch):
    def request(url, token, body, headers):
        assert url == "https://example.atlassian.net/rest/api/3/search/jql"
        assert token == ""
        assert (
            headers["Authorization"]
            == "Basic " + base64.b64encode(b"test@example.invalid:synthetic-token").decode()
        )
        assert body["jql"] == 'project = "RAMPI" ORDER BY key'
        return {
            "issues": [
                {
                    "key": "RAMPI-1",
                    "fields": {
                        "summary": "A task",
                        "status": {"name": "In Progress"},
                        "priority": {"name": "High"},
                        "description": {
                            "type": "doc",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Actual description"}],
                                }
                            ],
                        },
                    },
                }
            ]
        }

    monkeypatch.setattr(kanban, "request", request)
    board = kanban.jira(
        "https://example.atlassian.net#RAMPI",
        json.dumps({"email": "test@example.invalid", "token": "synthetic-token"}),
    )
    assert board.cards[0].description == "Actual description"
    assert board.cards[0].priority == "High"


def test_notion_paginates_data_sources_with_current_api_version(monkeypatch):
    calls = []

    def request(url, token, body, headers):
        calls.append(body.copy())
        assert "/v1/data_sources/" in url
        assert headers["Notion-Version"] == "2025-09-03"
        return {
            "results": [
                {
                    "id": str(len(calls)),
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "Task"}]},
                        "Status": {"type": "status", "status": {"name": "Review"}},
                    },
                }
            ],
            "has_more": len(calls) == 1,
            "next_cursor": "page-two",
        }

    monkeypatch.setattr(kanban, "request", request)
    board = kanban.notion("a" * 32, "synthetic-token")
    assert len(board.cards) == 2 and board.cards[0].status == "Review"
    assert calls[1]["start_cursor"] == "page-two"


def test_asana_rejects_foreign_pagination_host_before_forwarding_token(monkeypatch):
    def request(*args):
        return {"data": [], "next_page": {"uri": "https://attacker.invalid/read"}}

    monkeypatch.setattr(kanban, "request", request)
    with pytest.raises(ValueError, match="Asana-Paginierung"):
        kanban.asana("1234", "synthetic-token")
