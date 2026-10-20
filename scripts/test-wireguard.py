"""Real NetworkManager/WireGuard peers in disposable, private Docker namespaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path


def run(*args: str, input_text: str | None = None, check: bool = True, timeout: int = 30):
    result = subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        # stdout can contain ephemeral private keys; never put it in diagnostics.
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()[-2000:]}")
    return result


def serve() -> None:
    if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
        raise SystemExit("This mutation test requires its designated disposable container")
    if os.geteuid() != 0:
        raise SystemExit("Container setup requires root")
    Path("/run/dbus").mkdir(parents=True, exist_ok=True)
    Path("/etc/NetworkManager/conf.d/rampi-ci.conf").write_text(
        "[main]\nno-auto-default=*\n[keyfile]\n"
        "unmanaged-devices=interface-name:eth0;interface-name:lo\n"
        "[connectivity]\nenabled=false\n"
    )
    Path("/etc/polkit-1/rules.d/49-rampi-ci.rules").write_text(
        'polkit.addRule(function(action, subject) { if (subject.user === "rampi" && '
        '(action.id === "org.freedesktop.NetworkManager.settings.modify.own" || '
        'action.id === "org.freedesktop.NetworkManager.network-control")) '
        "{ return polkit.Result.YES; } });\n"
    )
    run("useradd", "--no-create-home", "rampi-other")
    run("dbus-daemon", "--system", "--fork")
    with subprocess.Popen(["NetworkManager", "--no-daemon", "--log-level=WARN"]) as manager:
        raise SystemExit(manager.wait())


def integration(image: str) -> None:
    suffix = uuid.uuid4().hex[:12]
    network = ""
    peers: list[str] = []

    def execute(peer: str, *args: str, user: str = "root", **kwargs):
        return run(
            "docker",
            "exec",
            "-i",
            "--user",
            user,
            "-e",
            f"USER={user}",
            "-e",
            f"LOGNAME={user}",
            "-e",
            "LC_ALL=C",
            peer,
            *args,
            **kwargs,
        )

    try:
        network = run(
            "docker", "network", "create", "--internal", f"rampi-wg-{suffix}"
        ).stdout.strip()
        for index in range(2):
            peer = run(
                "docker",
                "run",
                "--detach",
                "--rm",
                "--network",
                network,
                "--name",
                f"rampi-wg-{suffix}-{index}",
                "--user",
                "root",
                "--cap-add=NET_ADMIN",
                "--cap-add=NET_RAW",
                "--memory=512m",
                "--cpus=2",
                "--mount",
                f"type=bind,source={Path(__file__).resolve().parents[1]},target=/app,readonly",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                image,
                "python3",
                "-u",
                "scripts/test-wireguard.py",
                "--serve",
            ).stdout.strip()
            peers.append(peer)
            for _attempt in range(60):
                if execute(peer, "nmcli", "general", "status", check=False).returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Container NetworkManager did not become ready")
        addresses = []
        private_keys = []
        public_keys = []
        for peer in peers:
            data = json.loads(run("docker", "inspect", peer).stdout)[0]
            addresses.append(next(iter(data["NetworkSettings"]["Networks"].values()))["IPAddress"])
            key = execute(peer, "wg", "genkey").stdout.strip()
            private_keys.append(key)
            public_keys.append(execute(peer, "wg", "pubkey", input_text=key + "\n").stdout.strip())
        connections = []
        for index, peer in enumerate(peers):
            other = 1 - index
            configuration = (
                f"[Interface]\nPrivateKey={private_keys[index]}\n"
                f"Address=198.18.77.{index + 1}/32\nListenPort=51820\n"
                f"[Peer]\nPublicKey={public_keys[other]}\nAllowedIPs=198.18.77.{other + 1}/32\n"
                f"Endpoint={addresses[other]}:51820\nPersistentKeepalive=1\n"
            )
            execute(
                peer,
                "python3",
                "-c",
                "import os,sys; from pathlib import Path; "
                "os.umask(0o077); Path('/home/rampi/rampi-ci.conf').write_text(sys.stdin.read())",
                user="rampi",
                input_text=configuration,
            )
            output = execute(
                peer,
                "python3",
                "-c",
                "from rampi.services import wireguard_import; "
                "print(wireguard_import('/home/rampi/rampi-ci.conf'))",
                user="rampi",
            ).stdout
            match = re.search(r"UUID: ([0-9a-f-]{36})", output)
            if not match:
                raise RuntimeError("Rampi import did not return a connection UUID")
            connection = match[1]
            connections.append(connection)
            autostart = execute(
                peer, "nmcli", "-g", "connection.autoconnect", "connection", "show", connection
            )
            permissions = execute(
                peer,
                "nmcli",
                "--escape",
                "no",
                "-g",
                "connection.permissions",
                "connection",
                "show",
                connection,
            )
            if autostart.stdout.strip() != "no" or permissions.stdout.strip() != "user:rampi":
                raise RuntimeError(
                    "Real imported connection lost its private ACL or manual activation policy"
                )
            if execute(peer, "wg", "show", "rampi-ci", check=False).returncode == 0:
                raise RuntimeError("Import activated a tunnel without the user's request")
            visible = execute(
                peer,
                "nmcli",
                "--wait",
                "5",
                "--show-secrets",
                "-g",
                "connection.id",
                "connection",
                "show",
                "uuid",
                connection,
                user="rampi-other",
                check=False,
            )
            if visible.returncode == 0:
                raise RuntimeError("Another Linux user could read the private profile")
            foreign = execute(
                peer,
                "nmcli",
                "--wait",
                "5",
                "connection",
                "up",
                "uuid",
                connection,
                user="rampi-other",
                check=False,
            )
            if foreign.returncode == 0:
                raise RuntimeError("Another Linux user activated the private profile")
            execute(
                peer,
                "python3",
                "-c",
                "from rampi.services import network_action; "
                f"print(network_action('up', '{connection}'))",
                user="rampi",
                timeout=75,
            )
        for index, peer in enumerate(peers):
            other = 1 - index
            execute(peer, "ping", "-I", "rampi-ci", "-c", "3", "-W", "3", f"198.18.77.{other + 1}")
            handshake = execute(peer, "wg", "show", "rampi-ci", "latest-handshakes").stdout.split()
            transfer = execute(peer, "wg", "show", "rampi-ci", "transfer").stdout.split()
            if (
                len(handshake) != 2
                or int(handshake[1]) <= 0
                or len(transfer) != 3
                or min(map(int, transfer[1:])) <= 0
            ):
                raise RuntimeError(
                    "No real WireGuard handshake and bidirectional encrypted traffic"
                )
        wrong_key = execute(peers[1], "wg", "genkey").stdout
        execute(
            peers[1], "wg", "set", "rampi-ci", "private-key", "/dev/stdin", input_text=wrong_key
        )
        if (
            execute(
                peers[0], "ping", "-I", "rampi-ci", "-c", "1", "-W", "2", "198.18.77.2", check=False
            ).returncode
            == 0
        ):
            raise RuntimeError("Tunnel accepted a peer with the wrong private key")
        for peer, connection in zip(peers, connections, strict=True):
            execute(
                peer,
                "python3",
                "-c",
                "from rampi.services import network_action; "
                f"print(network_action('down', '{connection}'))",
                user="rampi",
                timeout=75,
            )
            if execute(peer, "wg", "show", "rampi-ci", check=False).returncode == 0:
                raise RuntimeError("Disconnect left the tunnel active")
        print(
            "PASS: real Rampi import and NetworkManager activation; private user ACLs; "
            "two WireGuard peers exchange encrypted traffic, reject a wrong key and disconnect."
        )
    finally:
        for peer in peers:
            run("docker", "rm", "--force", peer, check=False)
        if network:
            run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="rampi-trixie-test")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.serve:
        serve()
    else:
        integration(options.image)
