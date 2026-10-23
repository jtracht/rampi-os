"""Actual curl TLS, encrypted GNOME Keyring, GTK and provider contracts; no cloud accounts."""

import base64
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable container required")


def user_stage(secret_file):
    assert os.geteuid() == 1000
    credentials = json.loads(Path(secret_file).read_text())
    with tempfile.TemporaryDirectory(prefix="rampi-cloud-personal-") as temporary:
        home = Path(temporary)
        for name, folder in [
            ("HOME", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_RUNTIME_DIR", "runtime"),
        ]:
            path = home / folder
            path.mkdir(mode=0o700)
            os.environ[name] = str(path)
        subprocess.run(
            [
                "dbus-update-activation-environment",
                "HOME",
                "XDG_CONFIG_HOME",
                "XDG_DATA_HOME",
                "XDG_CACHE_HOME",
                "XDG_RUNTIME_DIR",
            ],
            check=True,
        )
        daemon = subprocess.Popen(
            ["gnome-keyring-daemon", "--unlock", "--components=secrets", "--foreground"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            assert daemon.stdin is not None
            daemon.stdin.write(uuid.uuid4().hex.encode())
            daemon.stdin.close()
            # Query the bus itself first: contacting Secret Service here can
            # auto-start a second daemon while the first writes its keyring.
            for _ in range(200):
                owner = subprocess.run(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--dest",
                        "org.freedesktop.DBus",
                        "--object-path",
                        "/org/freedesktop/DBus",
                        "--method",
                        "org.freedesktop.DBus.NameHasOwner",
                        "org.freedesktop.secrets",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if "true" in owner.stdout:
                    break
                if daemon.poll() is not None:
                    raise RuntimeError("Keyring daemon exited before acquiring its bus name")
                time.sleep(0.05)
            else:
                raise RuntimeError("Keyring daemon did not acquire its bus name")
            for _ in range(100):
                ready = subprocess.run(
                    [
                        "gdbus",
                        "call",
                        "--session",
                        "--dest",
                        "org.freedesktop.secrets",
                        "--object-path",
                        "/org/freedesktop/secrets",
                        "--method",
                        "org.freedesktop.Secret.Service.ReadAlias",
                        "default",
                    ],
                    capture_output=True,
                    text=True,
                )
                if ready.returncode == 0 and "collection" in ready.stdout:
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("Actual default keyring not ready: " + ready.stderr)
            # A user's curlrc must not change redirect, output or TLS policy.
            (Path(os.environ["HOME"]) / ".curlrc").write_text("location\ninsecure\n")
            prefix = (
                Path("tests/rust/run-wayland.sh")
                .read_text()
                .split("bash tests/rust/test-first-run.sh")[0]
            )
            script = home / "ui.sh"
            script.write_text(
                prefix + "timeout 45 /build/target/debug/rampi-native --kanban-cloud-ui-check\n"
            )
            for command in [
                ["bash", str(script)],
                ["/build/target/debug/rampi-native", "--kanban-cloud-check"],
            ]:
                result = subprocess.run(command, capture_output=True, text=True, timeout=120)
                for kind in ["github", "trello", "jira", "asana", "notion", "gitea"]:
                    assert credentials[kind]["token"] not in result.stdout + result.stderr
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                print(result.stdout.strip())
            keyrings = list((home / "data/keyrings").glob("*.keyring"))
            assert keyrings, "Real encrypted keyring file missing"
            for path in keyrings:
                assert path.stat().st_mode & 0o077 == 0
                for kind in ["github", "trello", "jira", "asana", "notion", "gitea"]:
                    assert credentials[kind]["token"].encode() not in path.read_bytes()
        finally:
            daemon.terminate()
            daemon.wait(timeout=10)


if len(sys.argv) > 1 and sys.argv[1] == "--user":
    user_stage(sys.argv[2])
    raise SystemExit(0)

if os.geteuid() != 0:
    raise SystemExit("Root is required only inside the disposable fixture container")
from graphql import parse  # noqa: E402


def checked(*args):
    subprocess.run(args, capture_output=True, check=True)


with tempfile.TemporaryDirectory(prefix="rampi-cloud-tls-") as temporary:
    root = Path(temporary)
    root.chmod(0o755)
    control = root / "control"
    control.mkdir(mode=0o700)
    os.chown(control, 1000, 1000)
    credentials = {
        kind: {"token": uuid.uuid4().hex + "+/="}
        for kind in ["github", "trello", "jira", "asana", "notion", "gitea"]
    }
    credentials["trello"]["account"] = uuid.uuid4().hex + "+/="
    credentials["jira"]["account"] = "fixture@example.invalid"
    secret = root / "fixture.json"
    secret.write_text(json.dumps(credentials))
    secret.chmod(0o600)
    os.chown(secret, 1000, 1000)
    hosts = [
        "api.github.com",
        "api.trello.com",
        "app.asana.com",
        "api.notion.com",
        "fixture.atlassian.net",
        "api.atlassian.com",
        "gitea.fixture.test",
    ]
    ca, ca_key, cert, key, csr = [
        str(root / name) for name in ["ca.crt", "ca.key", "server.crt", "server.key", "server.csr"]
    ]
    checked(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        ca_key,
        "-out",
        ca,
        "-days",
        "1",
        "-subj",
        "/CN=Rampi disposable cloud CA",
        "-addext",
        "basicConstraints=critical,CA:TRUE",
    )
    checked(
        "openssl",
        "req",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        key,
        "-out",
        csr,
        "-subj",
        "/CN=api.github.com",
    )
    extensions = root / "extensions"
    extensions.write_text(
        "subjectAltName="
        + ",".join("DNS:" + h for h in hosts)
        + "\nbasicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\n"
    )
    checked(
        "openssl",
        "x509",
        "-req",
        "-in",
        csr,
        "-CA",
        ca,
        "-CAkey",
        ca_key,
        "-CAcreateserial",
        "-days",
        "1",
        "-out",
        cert,
        "-extfile",
        str(extensions),
    )
    Path("/usr/local/share/ca-certificates/rampi-cloud-fixture.crt").write_bytes(
        Path(ca).read_bytes()
    )
    checked("update-ca-certificates")
    requests = []
    failures = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def send(self, body, status=200):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def route(self):
            host = self.headers["Host"]
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            body = (
                json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                if self.command == "POST"
                else None
            )
            requests.append((host, url.path, self.command))
            assert host in hosts
            assert self.command in ["GET", "POST"]
            if (control / "offline").exists():
                self.send({"error": "fixture offline"}, 503)
                return
            kind = {
                "api.github.com": "github",
                "api.trello.com": "trello",
                "app.asana.com": "asana",
                "api.notion.com": "notion",
                "fixture.atlassian.net": "jira",
                "api.atlassian.com": "jira",
                "gitea.fixture.test": "gitea",
            }[host]
            auth = self.headers["Authorization"]
            expected = "Bearer " + credentials[kind]["token"]
            if kind == "gitea":
                expected = "token " + credentials[kind]["token"]
            if kind == "trello":
                expected = (
                    'OAuth oauth_consumer_key="'
                    + urllib.parse.quote(credentials[kind]["account"], safe="")
                    + '", oauth_token="'
                    + urllib.parse.quote(credentials[kind]["token"], safe="")
                    + '"'
                )
            if kind == "jira" and host != "api.atlassian.com":
                expected = (
                    "Basic "
                    + base64.b64encode(
                        (credentials[kind]["account"] + ":" + credentials[kind]["token"]).encode()
                    ).decode()
                )
            assert auth == expected, "Actual TLS authorization mismatch"
            assert credentials[kind]["token"] not in self.path
            for process in Path("/proc").glob("[0-9]*/cmdline"):
                try:
                    assert credentials[kind]["token"].encode() not in process.read_bytes(), (
                        "Token leaked into process arguments"
                    )
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    pass
            if kind == "github":
                assert self.command == "POST" and url.path == "/graphql"
                document = parse(body["query"])
                assert all(
                    getattr(d, "operation", None).value == "query" for d in document.definitions
                )
                number = body["variables"]["number"]
                if number == 2:
                    self.send({"errors": [{"message": "fixture query failure"}]})
                    return
                if number == 4:
                    self.send_response(302)
                    self.send_header("Location", "https://unexpected.invalid/collect")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if number == 5:
                    self.send_response(200)
                    self.send_header("Content-Length", "4194305")
                    self.end_headers()
                    return
                if number == 6:
                    self.send({"error": auth}, 401)
                    return
                second = body["variables"]["after"] is not None
                card = {
                    "id": "item-2" if second else "item-1",
                    "isArchived": False,
                    "content": {
                        "title": "github second" if second else "github first",
                        "body": "Details",
                        "url": "https://github.com/fixture/repo/issues/1",
                        "repository": {"nameWithOwner": "fixture/repo"},
                    },
                    "fieldValues": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [{"name": "Review", "field": {"name": "Status"}}],
                    },
                }
                self.send(
                    {
                        "data": {
                            "organization": {
                                "projectV2": {
                                    "title": "GitHub fixture",
                                    "items": {
                                        "nodes": [card],
                                        "pageInfo": {
                                            "hasNextPage": not second or number == 3,
                                            "endCursor": "cursor2",
                                        },
                                    },
                                }
                            }
                        }
                    }
                )
            elif kind == "gitea":
                assert self.command == "GET"
                prefix = "/api/v1/repos/fixture/repo/projects/1"
                if url.path == prefix:
                    self.send({"id": 1, "title": "Gitea fixture"})
                elif url.path == prefix + "/columns":
                    self.send(
                        [
                            {"id": 2, "title": "Empty", "sorting": 2},
                            {"id": 1, "title": "Review", "sorting": 1},
                        ]
                        if query["page"] == ["1"]
                        else []
                    )
                else:
                    assert url.path in [prefix + "/columns/1/issues", prefix + "/columns/2/issues"]
                    page = int(query["page"][0])
                    # Deliberately cap the server at one row, despite limit=100.
                    self.send(
                        [
                            {
                                "id": page,
                                "title": "gitea first" if page == 1 else "gitea second",
                                "body": "Issue text",
                                "html_url": "https://gitea.fixture.test/fixture/repo/issues/1",
                            }
                        ]
                        if "/columns/1/" in url.path and page < 3
                        else []
                    )
            elif kind == "trello":
                assert self.command == "GET"
                if url.path.endswith("/lists"):
                    self.send([{"id": "list1", "name": "Review"}, {"id": "list2", "name": "Empty"}])
                else:
                    assert url.path.endswith("/cards")
                    if "before" in query:
                        assert query["before"] == [f"{1:024x}"]
                        self.send(
                            [
                                {
                                    "id": "0" * 24,
                                    "name": "trello last",
                                    "idList": "list1",
                                    "closed": False,
                                }
                            ]
                        )
                    else:
                        self.send(
                            [
                                {
                                    "id": f"{1000 - i:024x}",
                                    "name": "trello first" if i == 0 else f"Task {i}",
                                    "idList": "list1",
                                    "closed": False,
                                }
                                for i in range(1000)
                            ]
                        )
            elif kind == "asana":
                assert self.command == "GET" and url.path == "/api/1.0/projects/42/tasks"
                second = "offset" in query
                if second:
                    assert query["offset"] == ["opaque+/=cursor"]
                self.send(
                    {
                        "data": [
                            {
                                "gid": "2" if second else "1",
                                "name": "asana second" if second else "asana first",
                                "completed": second,
                                "notes": "Notes",
                                "memberships": [
                                    {"project": {"gid": "other"}, "section": {"name": "Wrong"}},
                                    {"project": {"gid": "42"}, "section": {"name": "Review"}},
                                ],
                            }
                        ],
                        "next_page": None
                        if second
                        else {
                            "offset": "opaque+/=cursor",
                            "uri": "https://unexpected.invalid/collect",
                        },
                    }
                )
            elif kind == "jira":
                assert self.command == "POST" and url.path.endswith("/rest/api/3/search/jql")
                assert body["jql"] == 'project = "RAMPI" ORDER BY key'
                second = "nextPageToken" in body
                self.send(
                    {
                        "issues": [
                            {
                                "key": "RAMPI-2" if second else "RAMPI-1",
                                "fields": {
                                    "summary": "jira second" if second else "jira first",
                                    "status": {"name": "Review"},
                                    "description": {
                                        "type": "doc",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "Alpha"},
                                                    {"type": "text", "text": "Beta"},
                                                ],
                                            }
                                        ],
                                    },
                                },
                            }
                        ],
                        "isLast": second,
                        **({} if second else {"nextPageToken": "opaque+/=cursor"}),
                    }
                )
            else:
                assert self.command == "POST" and url.path.endswith("/query")
                assert self.headers["Notion-Version"] == "2026-03-11"
                second = "start_cursor" in body
                self.send(
                    {
                        "results": [
                            {
                                "object": "page",
                                "id": "page2" if second else "page1",
                                "in_trash": False,
                                "properties": {
                                    "Title": {
                                        "type": "title",
                                        "title": [
                                            {
                                                "plain_text": "notion second"
                                                if second
                                                else "notion first"
                                            }
                                        ],
                                    },
                                    "Status": {"type": "status", "status": {"name": "Review"}},
                                },
                            }
                        ],
                        "has_more": not second,
                        "next_cursor": None if second else "opaque+/=cursor",
                    }
                )

        def do_GET(self):
            try:
                self.route()
            except Exception as error:
                failures.append(type(error).__name__)
                self.send({"error": "fixture assertion failed"}, 500)

        do_POST = do_GET

        def log_message(self, *args):
            pass

    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 443), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run(
            [
                "runuser",
                "-u",
                "rampi",
                "--",
                "dbus-run-session",
                "--",
                "python3",
                __file__,
                "--user",
                str(secret),
            ],
            env={
                **os.environ,
                "RAMPI_TEST_CLOUD_FILE": str(secret),
                "RAMPI_TEST_CLOUD_CONTROL": str(control),
                "RAMPI_TEST_CLOUD_TLS": "1",
            },
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode:
            raise RuntimeError(
                result.stdout + result.stderr + "\nServer assertions: " + str(failures)
            )
        assert not failures
        assert set(host for host, _, _ in requests) == set(hosts)
        assert "RAMPI_RUST_CLOUD_KANBAN_TLS_KEYRING_OK" in result.stdout
        assert "RAMPI_RUST_CLOUD_KANBAN_PAGE_OK" in result.stdout
        print(result.stdout.strip())
    finally:
        server.shutdown()
        server.server_close()
print(
    "PASS: real encrypted keyring, curl HTTPS, six provider contracts, pagination, "
    "private offline cache, redirect/size/error rejection and actual GTK; "
    "no personal cloud accounts."
)
