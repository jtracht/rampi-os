"""Read-only connectors. No task mutation method exists in this module."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from .config import atomic_json, cache_home, safe_url
from .process import command

MAX_BODY = 4 * 1024 * 1024


@dataclass
class Card:
    id: str
    title: str
    status: str = "Offen"
    description: str = ""
    priority: str = "normal"
    project: str = ""
    url: str = ""


@dataclass
class Board:
    title: str = "Kanban Board"
    columns: list[str] = field(default_factory=lambda: ["Offen", "In Arbeit", "Review", "Erledigt"])
    cards: list[Card] = field(default_factory=list)
    cached: bool = False
    warning: str = ""

    def view(self, query: str = "") -> dict[str, Any]:
        needle = query.casefold()
        visible = [
            c
            for c in self.cards
            if needle in f"{c.title} {c.description} {c.project} {c.priority}".casefold()
        ]
        columns = list(dict.fromkeys([*self.columns, *(c.status for c in visible)]))
        return {
            "title": self.title,
            "cached": self.cached,
            "warning": self.warning,
            "count": len(visible),
            "columns": [
                {"name": col, "cards": [asdict(c) for c in visible if c.status == col]}
                for col in columns
            ],
        }


def secret(key: str) -> str:
    if not key:
        return ""
    return command(["secret-tool", "lookup", "application", "rampi", "profile", key])


def store_token(profile: str, kind: str, account: str, token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", profile):
        raise ValueError("Schlüsselbund-Profil: 1–64 Buchstaben, Ziffern, _, . oder -.")
    if not token or len(token) > 8192 or "\x00" in token:
        raise ValueError("Ein gültiges Zugriffstoken eingeben.")
    value = token
    if kind == "trello":
        if not account:
            raise ValueError("Trello benötigt zusätzlich seinen API-Key.")
        value = json.dumps({"key": account, "token": token})
    elif kind == "jira" and account:
        value = json.dumps({"email": account, "token": token})
    command(
        [
            "secret-tool",
            "store",
            "--label=Rampi Kanban",
            "application",
            "rampi",
            "profile",
            profile,
        ],
        input_text=value,
        timeout=90,
    )
    return "Zugangsdaten im persönlichen System-Schlüsselbund gespeichert."


def request(
    url: str, token: str = "", body: dict | None = None, headers: dict[str, str] | None = None
) -> Any:
    safe_url(url)
    h = {"Accept": "application/json", "User-Agent": "Rampi/0.1", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)  # noqa: S310

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        # Never forward authorization to an untrusted redirected host.
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("API-Weiterleitungen sind aus Sicherheitsgründen deaktiviert.")

    with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as response:
        raw = response.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise ValueError("Die API-Antwort überschreitet 4 MiB.")
    return json.loads(raw)


def from_json(data: Any) -> Board:
    if not isinstance(data, dict) or not isinstance(data.get("cards", []), list):
        raise ValueError("Kanban benötigt ein Objekt mit einer cards-Liste.")
    columns = data.get("columns", ["Offen", "In Arbeit", "Review", "Erledigt"])
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise ValueError("columns muss eine Liste von Texten sein.")
    cards = []
    for index, raw in enumerate(data.get("cards", [])):
        if not isinstance(raw, dict) or not isinstance(raw.get("title"), str):
            raise ValueError(f"Karte {index + 1} hat keinen gültigen Titel.")
        values = {key: str(raw[key]) for key in Card.__dataclass_fields__ if key in raw}
        values.setdefault("id", str(index))
        cards.append(Card(**values))
    return Board(str(data.get("title", "Kanban Board")), columns, cards)


def github(source: str, token: str) -> Board:
    # source = organization/owner/project-number or user/owner/project-number
    match = re.fullmatch(r"(organization|user)/([A-Za-z0-9_.-]+)/([0-9]+)", source)
    if not match:
        raise ValueError("GitHub-Quelle: organization/NAME/NUMMER oder user/NAME/NUMMER")
    kind, owner, number = match.groups()
    query = """query($owner:String!,$number:Int!,$after:String){ROOT(login:$owner){
      projectV2(number:$number){title items(first:100,after:$after){pageInfo{hasNextPage endCursor}
        nodes{id content{... on Issue{title body url repository{nameWithOwner}}
        ... on PullRequest{title body url repository{nameWithOwner}} ... on DraftIssue{title body}}
        fieldValues(first:30){nodes{... on ProjectV2ItemFieldSingleSelectValue{name
        field{... on ProjectV2SingleSelectField{name}}}}}}}}}}""".replace("ROOT", kind)
    board = Board()
    cursor = None
    for _ in range(100):
        data = request(
            "https://api.github.com/graphql",
            token,
            {"query": query, "variables": {"owner": owner, "number": int(number), "after": cursor}},
        )
        if data.get("errors"):
            raise ValueError("GitHub Projects: Zugriff oder GraphQL-Abfrage fehlgeschlagen.")
        project = data["data"][kind]["projectV2"]
        if not project:
            raise ValueError("GitHub Project nicht gefunden oder nicht lesbar.")
        board.title = project["title"]
        for node in project["items"]["nodes"]:
            content = node.get("content")
            if not content:
                continue
            fields = {
                v["field"]["name"]: v["name"] for v in node["fieldValues"]["nodes"] if "name" in v
            }
            board.cards.append(
                Card(
                    node["id"],
                    content["title"],
                    fields.get("Status", "Offen"),
                    content.get("body", ""),
                    fields.get("Priority", "normal"),
                    content.get("repository", {}).get("nameWithOwner", ""),
                    content.get("url", ""),
                )
            )
        info = project["items"]["pageInfo"]
        if not info["hasNextPage"]:
            return board
        cursor = info["endCursor"]
    raise ValueError("GitHub Project überschreitet das Limit von 10.000 Einträgen.")


def asana(source: str, token: str) -> Board:
    if not source.isdigit():
        raise ValueError("Asana-Quelle muss eine numerische Projekt-ID sein.")
    board = Board("Asana")
    url = f"https://app.asana.com/api/1.0/projects/{source}/tasks?" + urlencode(
        {"limit": 100, "opt_fields": "name,notes,completed,memberships.section.name,permalink_url"}
    )
    for _ in range(100):
        data = request(url, token)
        for card in data["data"]:
            memberships = card.get("memberships", [])
            status = (
                "Erledigt"
                if card.get("completed")
                else next((m["section"]["name"] for m in memberships if m.get("section")), "Offen")
            )
            board.cards.append(
                Card(
                    card["gid"],
                    card["name"],
                    status,
                    card.get("notes", ""),
                    url=card.get("permalink_url", ""),
                )
            )
        next_page = data.get("next_page")
        if not next_page:
            return board
        url = next_page["uri"]
        if urlsplit(url).hostname != "app.asana.com":
            raise ValueError("Ungültige Asana-Paginierung.")
    raise ValueError("Asana-Paginierung überschreitet das Limit.")


def trello(source: str, token: str) -> Board:
    if not re.fullmatch(r"[A-Za-z0-9]+", source):
        raise ValueError("Ungültige Trello-Board-ID.")
    credentials = json.loads(token)  # Secret Service entry: {"key": "...", "token": "..."}
    auth = {
        "Authorization": 'OAuth oauth_consumer_key="'
        + quote(credentials["key"], safe="")
        + '", oauth_token="'
        + quote(credentials["token"], safe="")
        + '"'
    }
    lists = request(f"https://api.trello.com/1/boards/{source}/lists", headers=auth)
    cards = request(f"https://api.trello.com/1/boards/{source}/cards", headers=auth)
    names = {item["id"]: item["name"] for item in lists}
    return Board(
        "Trello",
        list(names.values()),
        [
            Card(
                c["id"],
                c["name"],
                names.get(c["idList"], "Offen"),
                c.get("desc", ""),
                url=c.get("url", ""),
            )
            for c in cards
            if not c.get("closed")
        ],
    )


def jira(source: str, token: str) -> Board:
    # source is HTTPS site URL followed by #PROJECTKEY; token is a scoped OAuth token.
    site, sep, project = source.partition("#")
    safe_url(site)
    if not sep or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project):
        raise ValueError("Jira-Quelle: https://SITE.atlassian.net#PROJEKT")
    origin = urlsplit(site)
    if origin.query:
        raise ValueError("Bitte keine Queryparameter in der Jira-Quelle verwenden.")
    auth: dict[str, str] = {}
    bearer = token
    if origin.hostname and origin.hostname.endswith(".atlassian.net"):
        if origin.path not in {"", "/"}:
            raise ValueError("Bitte nur die Jira-Site-Adresse angeben.")
        try:
            credentials = json.loads(token)
            encoded = base64.b64encode(
                (credentials["email"] + ":" + credentials["token"]).encode()
            ).decode()
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(
                'Jira Cloud benötigt im Secret Service {"email":…,"token":…}.'
            ) from exc
        auth["Authorization"] = "Basic " + encoded
        bearer = ""
    elif origin.hostname != "api.atlassian.com" or not re.fullmatch(
        r"/ex/jira/[a-fA-F0-9-]{36}/?", origin.path
    ):
        raise ValueError("Jira: Cloud-Site mit E-Mail/API-Token oder OAuth-Cloud-ID verwenden.")
    board = Board(project)
    cursor = None
    for _ in range(100):
        body: dict[str, Any] = {
            "jql": f'project = "{project}" ORDER BY key',
            "maxResults": 100,
            "fields": ["summary", "status", "description", "priority"],
        }
        if cursor:
            body["nextPageToken"] = cursor
        data = request(site.rstrip("/") + "/rest/api/3/search/jql", bearer, body, auth)
        for issue in data["issues"]:
            f = issue["fields"]
            board.cards.append(
                Card(
                    issue["key"],
                    f["summary"],
                    f["status"]["name"],
                    description_text(f.get("description")),
                    (f.get("priority") or {}).get("name", "normal"),
                    project,
                    site.rstrip("/") + "/browse/" + issue["key"],
                )
            )
        cursor = data.get("nextPageToken")
        if not cursor:
            return board
    raise ValueError("Jira-Paginierung überschreitet das Limit.")


def description_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    if value.get("type") == "text":
        return str(value.get("text", ""))
    separator = "\n" if value.get("type") in {"doc", "bulletList", "orderedList"} else ""
    return separator.join(description_text(item) for item in value.get("content", []))


def notion(source: str, token: str) -> Board:
    if not re.fullmatch(r"[a-fA-F0-9-]{32,36}", source):
        raise ValueError("Notion benötigt eine Data-Source-ID.")
    board = Board("Notion")
    cursor = None
    for _ in range(100):
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = request(
            f"https://api.notion.com/v1/data_sources/{source}/query",
            token,
            body,
            {"Notion-Version": "2025-09-03"},
        )
        for page in data["results"]:
            props = page["properties"].values()
            title = next(
                (
                    "".join(t["plain_text"] for t in p["title"])
                    for p in props
                    if p["type"] == "title"
                ),
                "Ohne Titel",
            )
            status = next(
                (
                    (p.get("status") or {}).get("name", "Offen")
                    for p in props
                    if p["type"] == "status"
                ),
                "Offen",
            )
            board.cards.append(Card(page["id"], title, status, url=page.get("url", "")))
        if not data.get("has_more"):
            return board
        cursor = data["next_cursor"]
    raise ValueError("Notion-Paginierung überschreitet das Limit.")


CONNECTORS = {"github": github, "asana": asana, "trello": trello, "jira": jira, "notion": notion}


def load_board(kind: str, source: str, token_key: str = "") -> Board:
    if not source:
        return Board(warning="Noch keine Datenquelle eingerichtet.")
    digest = hashlib.sha256(f"{kind}:{source}:{token_key}".encode()).hexdigest()
    cache = cache_home() / f"board-{digest}.json"
    try:
        if kind == "json":
            path = Path(source).expanduser()
            if path.stat().st_size > MAX_BODY:
                raise ValueError("Kanban-Datei überschreitet 4 MiB.")
            board = from_json(json.loads(path.read_text(encoding="utf-8")))
        elif kind in CONNECTORS:
            board = CONNECTORS[kind](source, secret(token_key))
        else:
            raise ValueError("Unbekannter Connector.")
        atomic_json(cache, asdict(board))
        return board
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        if cache.exists():
            board = from_json(json.loads(cache.read_text(encoding="utf-8")))
            board.cached = True
            board.warning = "Offline-Cache · Aktualisierung fehlgeschlagen."
            return board
        raise
