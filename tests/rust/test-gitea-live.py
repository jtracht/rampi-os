"""Real pinned Gitea HTTPS, read-only token, GTK/keyring, refresh and offline cache.

Only newly created, privately networked Docker resources are changed. No model
requests, personal accounts, published ports, or mock provider responses.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

GITEA = (
    "docker.gitea.com/gitea:28.2.0@sha256:"
    "30777c91280d973fa02be48b1ade735bd6859e8f6f7af3b4444d519437852504"
)


def run(*command, data=None, check=True, timeout=120):
    result = subprocess.run(command, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Commands can handle fresh disposable credentials: never echo argv/stdin.
        raise RuntimeError(f"Disposable Gitea operation failed ({result.returncode})")
    return result


def client():
    if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").is_file():
        raise RuntimeError("Disposable client required")
    credential = json.loads(sys.stdin.buffer.read())
    ca = Path("/usr/local/share/ca-certificates/rampi-live-gitea.crt")
    ca.write_text(credential.pop("ca"))
    run("update-ca-certificates")
    descriptor, filename = tempfile.mkstemp(prefix="rampi-live-gitea-")
    os.close(descriptor)
    secret = Path(filename)
    secret.write_text(json.dumps(credential))
    secret.chmod(0o600)
    os.chown(secret, 1000, 1000)
    os.environ["RAMPI_TEST_CLOUD_FILE"] = str(secret)
    binary = Path("/build/target/debug/rampi-native").read_bytes()
    Path(os.environ["RAMPI_TEST_ARTIFACTS"], "gitea-program-sha256.txt").write_text(
        hashlib.sha256(binary).hexdigest() + "\n"
    )
    try:
        result = run(
            "runuser",
            "-u",
            "rampi",
            "--",
            "dbus-run-session",
            "--",
            "python3",
            "tests/rust/test-cloud-kanban.py",
            "--gitea-live-user",
            str(secret),
            check=False,
            timeout=140,
        )
        assert credential["gitea"]["token"].encode() not in result.stdout + result.stderr
        sys.stdout.buffer.write(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Actual Gitea GTK/keyring acceptance failed")
    finally:
        secret.unlink(missing_ok=True)


def orchestrate(args):
    root = Path(__file__).resolve().parents[2]
    artifacts = Path(args.artifacts).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    for name in ("refresh", "offline"):
        for suffix in ("ready", "continue"):
            (artifacts / f"gitea-{name}-{suffix}").unlink(missing_ok=True)
    key = "rampi-gitea-" + uuid.uuid4().hex[:12]
    network, volume, server = key + "-net", key + "-data", key + "-server"
    tokens = []
    finished = threading.Event()
    failures = []

    def cli(*arguments):
        return (
            run(
                "docker",
                "exec",
                "--user",
                "1000:1000",
                server,
                "/usr/local/bin/gitea",
                "--config",
                "/data/gitea/conf/app.ini",
                *arguments,
            )
            .stdout.decode()
            .strip()
        )

    def api(path, token=None, method="GET", body=None, expected=200):
        config = [
            'url = "https://gitea-server:3000/api/v1' + path + '"',
            'cacert = "/data/gitea/cert.pem"',
            'request = "' + method + '"',
        ]
        if token:
            config.append('header = "Authorization: token ' + token + '"')
        if body is not None:
            config += [
                'header = "Content-Type: application/json"',
                "data = " + json.dumps(json.dumps(body)),
            ]
        response = run(
            "docker",
            "exec",
            "-i",
            server,
            "curl",
            "--disable",
            "--config",
            "-",
            "--silent",
            "--max-time",
            "10",
            "--write-out",
            "\n%{http_code}",
            data=("\n".join(config) + "\n").encode(),
        ).stdout
        payload, status = response.rsplit(b"\n", 1)
        if int(status) != expected:
            raise RuntimeError(f"Actual Gitea API {method} {path}: HTTP {status.decode()}")
        return json.loads(payload) if payload.strip() else None

    run("docker", "network", "create", "--internal", network)
    try:
        run("docker", "volume", "create", volume)
        # Existing official Gitea cert implementation; no custom TLS and no -k.
        setup = """set -eu
mkdir -p /data/gitea/conf /data/git/repositories
cat > /data/gitea/conf/app.ini
chown -R 1000:1000 /data/gitea /data/git
chmod 700 /data/gitea /data/gitea/conf
su git -s /bin/sh -c '/usr/local/bin/gitea cert --host gitea-server,localhost \\
 --ca --duration 24h --out /data/gitea/cert.pem --keyout /data/gitea/key.pem'
chmod 600 /data/gitea/key.pem /data/gitea/conf/app.ini
"""
        config = """RUN_MODE = prod
RUN_USER = git
[database]
DB_TYPE = sqlite3
PATH = /data/gitea/gitea.db
[repository]
ROOT = /data/git/repositories
[server]
PROTOCOL = https
HTTP_ADDR = 0.0.0.0
HTTP_PORT = 3000
ROOT_URL = https://gitea-server:3000/
APP_DATA_PATH = /data/gitea
CERT_FILE = /data/gitea/cert.pem
KEY_FILE = /data/gitea/key.pem
DISABLE_SSH = true
OFFLINE_MODE = true
[security]
INSTALL_LOCK = true
[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true
[log]
MODE = console
LEVEL = Warn
[api]
MAX_RESPONSE_ITEMS = 1
DEFAULT_PAGING_NUM = 1
"""
        run(
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--entrypoint",
            "sh",
            "--mount",
            f"type=volume,source={volume},target=/data",
            GITEA,
            "-c",
            setup,
            data=config.encode(),
        )
        run(
            "docker",
            "run",
            "-d",
            "--name",
            server,
            "--network",
            network,
            "--network-alias",
            "gitea-server",
            "--user",
            "1000:1000",
            "--memory",
            "512m",
            "--memory-swap",
            "512m",
            "--cpus",
            "2",
            "--mount",
            f"type=volume,source={volume},target=/data",
            "--entrypoint",
            "/usr/local/bin/gitea",
            GITEA,
            "--config",
            "/data/gitea/conf/app.ini",
            "web",
        )
        for _ in range(120):
            ready = run(
                "docker",
                "exec",
                server,
                "curl",
                "--silent",
                "--fail",
                "--cacert",
                "/data/gitea/cert.pem",
                "https://localhost:3000/api/healthz",
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Real HTTPS Gitea did not become ready")
        cli(
            "admin",
            "user",
            "create",
            "--username",
            "rampitest",
            "--email",
            "rampi@example.invalid",
            "--random-password",
            "--must-change-password=false",
        )
        for name, scopes in [("setup", "all"), ("reader", "read:repository,read:issue")]:
            tokens.append(
                cli(
                    "admin",
                    "user",
                    "generate-access-token",
                    "--username",
                    "rampitest",
                    "--token-name",
                    name,
                    "--raw",
                    "--scopes",
                    scopes,
                )
            )
        setup_token, reader = tokens
        api(
            "/user/repos",
            setup_token,
            "POST",
            {"name": "board", "private": True, "auto_init": True},
            expected=201,
        )
        base = "/repos/rampitest/board"
        title = "Rampi " + uuid.uuid4().hex
        project = api(
            base + "/projects",
            setup_token,
            "POST",
            {"title": title, "template_type": "none", "card_type": "text_only"},
            201,
        )
        endpoint = base + "/projects/" + str(project["id"])
        column = api(
            endpoint + "/columns", setup_token, "POST", {"title": "Review", "color": "#112233"}, 201
        )
        api(endpoint + "/columns", setup_token, "POST", {"title": "Empty"}, 201)
        issues = []
        for suffix in ("first", "second"):
            issue = api(
                base + "/issues",
                setup_token,
                "POST",
                {"title": "Rampi " + suffix, "body": "Grüße from actual Gitea"},
                201,
            )
            issues.append(issue)
            api(
                endpoint + f"/columns/{column['id']}/issues/{issue['id']}",
                setup_token,
                "POST",
                expected=201,
            )
        api(base + "/issues", reader, "POST", {"title": "forbidden"}, 403)
        ca = run("docker", "exec", server, "cat", "/data/gitea/cert.pem").stdout.decode()
        credentials = {
            "gitea": {
                "token": reader,
                "title": title,
                "source": f"https://gitea-server:3000/rampitest/board/projects/{project['id']}",
            },
            "ca": ca,
        }

        observations = []

        def controller():
            try:
                for phase in ("refresh", "offline"):
                    while not finished.wait(0.1):
                        if (artifacts / f"gitea-{phase}-ready").is_file():
                            break
                    else:
                        return
                    if phase == "refresh":
                        api(
                            base + f"/issues/{issues[0]['number']}",
                            setup_token,
                            "PATCH",
                            {"title": "Rampi first updated"},
                            201,
                        )
                    else:
                        # Confirm the client did not mutate the project or add issues.
                        actual = []
                        for page in range(1, 4):
                            rows = api(base + f"/issues?limit=1&page={page}", setup_token)
                            assert len(rows) == (0 if page == 3 else 1)
                            actual.extend(rows)
                        assert {row["id"] for row in actual} == {row["id"] for row in issues}
                        assert {row["title"] for row in actual} == {
                            "Rampi first updated",
                            "Rampi second",
                        }
                        observations.extend(
                            {"id": row["id"], "title": row["title"]} for row in actual
                        )
                        run("docker", "stop", "--time", "5", server)
                    (artifacts / f"gitea-{phase}-continue").write_text(phase)
            except Exception as error:
                failures.append(str(error))

        watcher = threading.Thread(target=controller)
        watcher.start()
        try:
            result = run(
                "docker",
                "run",
                "--rm",
                "-i",
                "--network",
                network,
                "--memory",
                "1g",
                "--memory-swap",
                "1g",
                "--cpus",
                "4",
                "--mount",
                f"type=bind,source={root.as_posix()},target=/src,readonly",
                "--mount",
                f"type=bind,source={artifacts.as_posix()},target=/artifacts",
                "--mount",
                "type=volume,source=rampi-rust-build,target=/build,readonly",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                "-e",
                "RAMPI_TEST_ARTIFACTS=/artifacts",
                args.image,
                "python3",
                "tests/rust/test-gitea-live.py",
                "--client",
                data=json.dumps(credentials).encode(),
                check=False,
                timeout=160,
            )
        finally:
            finished.set()
            watcher.join(timeout=20)
        log = result.stdout + result.stderr
        assert all(token.encode() not in log for token in tokens)
        (artifacts / "gitea-live.log").write_bytes(log)
        sys.stdout.buffer.write(log)
        if failures:
            raise RuntimeError("Gitea controller: " + str(failures))
        if result.returncode or b"RAMPI_RUST_GITEA_LIVE_PAGE_OK" not in log:
            raise RuntimeError("Actual Gitea acceptance did not pass")
        (artifacts / "gitea-environment.json").write_text(
            json.dumps(
                {
                    "image": GITEA,
                    "version": cli_version,
                    "private_network": True,
                    "published_ports": False,
                    "read_only_write_denied_http": 403,
                    "page_size": 1,
                    "cards": 2,
                    "refresh": True,
                    "offline": True,
                    "actual_server_issues": observations,
                    "binary_sha256": (artifacts / "gitea-program-sha256.txt").read_text().strip(),
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        finished.set()
        # Never touch an existing container/network: these names are fresh UUIDs.
        log = run("docker", "logs", server, check=False)
        raw = log.stdout + log.stderr
        if all(token.encode() not in raw for token in tokens):
            (artifacts / "gitea-server.log").write_bytes(raw)
        run("docker", "rm", "-f", server, check=False)
        run("docker", "volume", "rm", volume, check=False)
        run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--image", default="rampi-rust-dev")
    parser.add_argument("--artifacts", default="artifacts/gitea-live")
    options = parser.parse_args()
    if options.client:
        client()
    else:
        cli_version = (
            run(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "/usr/local/bin/gitea",
                GITEA,
                "--version",
            )
            .stdout.decode()
            .strip()
        )
        orchestrate(options)
