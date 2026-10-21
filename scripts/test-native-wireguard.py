"""Actual Rust/libnm/GIO import and encrypted WireGuard traffic in private Docker peers."""

import argparse
import json
import runpy
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Reuse the established guarded NetworkManager test service and command runner.
run = runpy.run_path(str(ROOT / "scripts/test-wireguard.py"))["run"]


def integration(image):
    suffix = uuid.uuid4().hex[:12]
    network = ""
    peers = []

    def execute(peer, *args, user="root", **kwargs):
        return run("docker", "exec", "-i", "--user", user, peer, *args, **kwargs)

    def action(peer, name, value=None, user="rampi", **kwargs):
        arguments = ["/build/target/debug/rampi-native", "--vpn-action", name]
        if value is not None:
            arguments.append(value)
        return execute(peer, *arguments, user=user, **kwargs)

    try:
        network = run(
            "docker", "network", "create", "--internal", f"rampi-native-wg-{suffix}"
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
                f"rampi-native-wg-{suffix}-{index}",
                "--user",
                "root",
                "--cap-add=NET_ADMIN",
                "--cap-add=NET_RAW",
                "--memory=512m",
                "--cpus=2",
                "--mount",
                f"type=bind,source={ROOT},target=/src,readonly",
                "--mount",
                "type=volume,source=rampi-rust-build,target=/build,readonly",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                image,
                "python3",
                "-u",
                "scripts/test-wireguard.py",
                "--serve",
            ).stdout.strip()
            peers.append(peer)
            for _ in range(60):
                if execute(peer, "nmcli", "general", "status", check=False).returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Isolated NetworkManager did not start")

        addresses = []
        private_keys = []
        public_keys = []
        for peer in peers:
            data = json.loads(run("docker", "inspect", peer).stdout)[0]
            addresses.append(next(iter(data["NetworkSettings"]["Networks"].values()))["IPAddress"])
            key = execute(peer, "wg", "genkey").stdout.strip()
            private_keys.append(key)
            public_keys.append(execute(peer, "wg", "pubkey", input_text=key + "\n").stdout.strip())

        identifiers = []
        for index, peer in enumerate(peers):
            other = 1 - index
            configuration = (
                f"[Interface]\nPrivateKey={private_keys[index]}\n"
                f"Address=198.18.77.{index + 1}/32\nListenPort=51820\n"
                f"[Peer]\nPublicKey={public_keys[other]}\n"
                f"AllowedIPs=198.18.77.{other + 1}/32\nEndpoint={addresses[other]}:51820\n"
                "PersistentKeepalive=1\n"
            )
            execute(
                peer,
                "python3",
                "-c",
                "import os,sys; from pathlib import Path; os.umask(0o077); "
                "Path('/home/rampi/rampi-ci.conf').write_text(sys.stdin.read())",
                user="rampi",
                input_text=configuration,
            )
            action(peer, "import", "/home/rampi/rampi-ci.conf")
            profiles = json.loads(action(peer, "list").stdout)
            if len(profiles) != 1 or profiles[0]["active"]:
                raise RuntimeError("Rust import was missing or automatically activated")
            identifier = profiles[0]["uuid"]
            identifiers.append(identifier)
            execute(
                peer,
                "nmcli",
                "connection",
                "modify",
                "uuid",
                identifier,
                "connection.id",
                "Personal: VPN\\Lab",
            )
            shared = execute(
                peer,
                "nmcli",
                "-g",
                "connection.uuid",
                "connection",
                "add",
                "type",
                "wireguard",
                "ifname",
                "rampi-shared",
                "con-name",
                "Shared: VPN",
            )
            # Query the UUID separately because nmcli add output is human-readable.
            shared_id = execute(
                peer, "nmcli", "-g", "connection.uuid", "connection", "show", "Shared: VPN"
            ).stdout.strip()
            if (
                not shared.returncode == 0
                or action(peer, "up", shared_id, check=False).returncode == 0
            ):
                raise RuntimeError("Rust allowed activation of a shared profile")
            own = json.loads(action(peer, "list").stdout)
            foreign = json.loads(action(peer, "list", user="rampi-other").stdout)
            if len(own) != 1 or own[0]["name"] != "Personal: VPN\\Lab" or foreign:
                raise RuntimeError("Rust picker leaked shared or foreign profile metadata")
            if action(peer, "up", identifier, user="rampi-other", check=False).returncode == 0:
                raise RuntimeError("A different Linux account activated the private tunnel")
            acl = execute(
                peer,
                "nmcli",
                "--escape",
                "no",
                "-g",
                "connection.permissions",
                "connection",
                "show",
                identifier,
            ).stdout.strip()
            autostart = execute(
                peer, "nmcli", "-g", "connection.autoconnect", "connection", "show", identifier
            ).stdout.strip()
            if acl != "user:rampi" or autostart != "no":
                raise RuntimeError("Real profile storage lost private ACL or manual activation")
            if (
                execute(
                    peer,
                    "nmcli",
                    "--show-secrets",
                    "-g",
                    "wireguard.private-key",
                    "connection",
                    "show",
                    identifier,
                    user="rampi-other",
                    check=False,
                ).returncode
                == 0
            ):
                raise RuntimeError("Another Linux account could read the private key")
            action(peer, "up", identifier)
            for _ in range(50):
                if json.loads(action(peer, "list").stdout)[0]["active"]:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Rust profile state never reached activated")

        for index, peer in enumerate(peers):
            execute(peer, "ping", "-I", "rampi-ci", "-c", "3", "-W", "3", f"198.18.77.{2 - index}")
            handshake = execute(peer, "wg", "show", "rampi-ci", "latest-handshakes").stdout.split()
            traffic = execute(peer, "wg", "show", "rampi-ci", "transfer").stdout.split()
            if (
                len(handshake) != 2
                or int(handshake[1]) <= 0
                or len(traffic) != 3
                or min(map(int, traffic[1:])) <= 0
            ):
                raise RuntimeError("Missing real handshake or bidirectional encrypted traffic")
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
        for peer, identifier in zip(peers, identifiers, strict=True):
            action(peer, "down", identifier)
            for _ in range(50):
                if execute(peer, "wg", "show", "rampi-ci", check=False).returncode != 0:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Rust disconnect left the WireGuard interface active")
        print("RAMPI_RUST_WIREGUARD_PEERS_OK")
        print(
            "PASS: actual Rust import/activation, Linux account isolation, encrypted traffic, "
            "wrong-key rejection and disconnect; no physical hardware."
        )
    finally:
        for peer in peers:
            run("docker", "rm", "--force", peer, check=False)
        if network:
            run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="rampi-rust-dev")
    integration(parser.parse_args().image)
