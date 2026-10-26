"""Real Tailscale data plane with an existing isolated Headscale coordinator.

Private Docker DNS aliases exercise the production login-origin restriction;
neither the public Tailscale service nor provider OAuth is impersonated outside
this disposable private network. No personal account or device is contacted.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
import urllib.parse
import uuid
from pathlib import Path

CONFIG = "/src/tests/vpn/headscale.json"
PROGRAM = "/build/target/debug/rampi-native"


def run(*args, data=None, check=True, timeout=90):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Auth IDs are one-time capabilities. Never print arguments or raw API output.
        raise RuntimeError(f"Private VPN fixture operation failed: {args[0]} ({result.returncode})")
    return result


def isolated():
    if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").is_file():
        raise RuntimeError("Disposable Linux VPN container required")


def control():
    isolated()
    os.umask(0o077)
    root = Path("/run/rampi-vpn-control")
    root.mkdir(mode=0o700)
    run(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-days",
        "1",
        "-subj",
        "/CN=Private Rampi VPN fixture CA",
        "-addext",
        "basicConstraints=critical,CA:TRUE",
        "-keyout",
        str(root / "ca.key"),
        "-out",
        str(root / "ca.crt"),
    )
    run(
        "openssl",
        "req",
        "-new",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-subj",
        "/CN=login.tailscale.com",
        "-keyout",
        str(root / "server.key"),
        "-out",
        str(root / "server.csr"),
    )
    extensions = root / "extensions.conf"
    extensions.write_text("subjectAltName=DNS:login.tailscale.com,DNS:controlplane.tailscale.com\n")
    run(
        "openssl",
        "x509",
        "-req",
        "-in",
        str(root / "server.csr"),
        "-CA",
        str(root / "ca.crt"),
        "-CAkey",
        str(root / "ca.key"),
        "-CAcreateserial",
        "-days",
        "1",
        "-extfile",
        str(extensions),
        "-out",
        str(root / "server.crt"),
    )
    subprocess.run(["headscale", "-c", CONFIG, "serve"], check=True)


def peer():
    isolated()
    os.umask(0o077)
    ca = Path("/run/rampi-vpn-ca.crt")
    for _ in range(300):
        if ca.is_file():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Private fixture CA was not supplied")
    shutil.copyfile(ca, "/usr/local/share/ca-certificates/rampi-vpn-fixture.crt")
    Path("/usr/local/share/ca-certificates/rampi-vpn-fixture.crt").chmod(0o644)
    run("update-ca-certificates")
    socket = Path("/run/tailscale/tailscaled.sock")
    if socket.exists():
        raise RuntimeError("An existing daemon must not be replaced")
    socket.parent.mkdir(exist_ok=True)
    os.chown(socket.parent, 0, 0)
    socket.parent.chmod(0o755)
    Path("/dev/net").mkdir(exist_ok=True)
    if not Path("/dev/net/tun").exists():
        os.mknod("/dev/net/tun", stat.S_IFCHR | 0o600, os.makedev(10, 200))
    run("useradd", "--create-home", "--shell", "/bin/bash", "vpn-other")
    # The official system daemon creates and owns its state. No kernel/crypto/VPN
    # implementation, userspace fake interface or host-network namespace is used.
    log = Path("/run/rampi-tailscaled.log").open("wb")
    with log:
        subprocess.run(
            [
                "tailscaled",
                "--state=/run/rampi-tailscale.state",
                "--socket=" + str(socket),
                "--tun=tailscale0",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def integration(args):
    root = Path(__file__).resolve().parents[2]
    output = args.artifacts.resolve()
    output.mkdir(parents=True, exist_ok=True)
    key = uuid.uuid4().hex[:12]
    network, coordinator = "rampi-ts-net-" + key, "rampi-ts-control-" + key
    peers = ["rampi-ts-" + key + "-" + str(i) for i in range(2)]
    capabilities = []
    profile_operator_setup = []
    preferences = []
    preference_keys = (
        "ControlURL", "RouteAll", "CorpDNS", "Hostname", "OperatorUser",
        "ExitNodeID", "ExitNodeIP", "AdvertiseRoutes", "AllowSingleHosts",
    )

    def execute(container, *command, user="root", **kwargs):
        return run("docker", "exec", "-i", "--user", user, container, *command, **kwargs)

    def hs(*command, **kwargs):
        return execute(coordinator, "headscale", "-c", CONFIG, "-o", "json", *command, **kwargs)

    def status(container):
        return json.loads(execute(container, "tailscale", "status", "--json").stdout)

    def action(container, operation, user="rampi"):
        result = execute(container, PROGRAM, "--tailscale-check", operation, user=user, check=False)
        if result.returncode:
            diagnostic = (result.stdout + result.stderr).decode(errors="replace")
            for capability in capabilities:
                diagnostic = diagnostic.replace(capability, "<private-registration-redacted>")
            (output / (operation + "-error.log")).write_text(diagnostic)
            observed = status(container)
            (output / (operation + "-state.json")).write_text(
                json.dumps({"BackendState": observed.get("BackendState"),
                            "online": observed.get("Self", {}).get("Online")}, indent=2) + "\n"
            )
            if operation == "action-down":
                probe = execute(container, "tailscale", "down", user=user, check=False)
                diagnostic = (probe.stdout + probe.stderr).decode(errors="replace")
                for capability in capabilities:
                    diagnostic = diagnostic.replace(capability, "<private-registration-redacted>")
                (output / "down-cli-diagnostic.log").write_text(
                    f"exit={probe.returncode}\n" + diagnostic
                )
            elif operation == "action-up":
                probe = execute(container, "tailscale", "up", "--timeout=3s", "--json",
                                user=user, check=False)
                diagnostic = (probe.stdout + probe.stderr).decode(errors="replace")
                for capability in capabilities:
                    diagnostic = diagnostic.replace(capability, "<private-registration-redacted>")
                (output / "up-cli-diagnostic.log").write_text(
                    f"exit={probe.returncode}\n" + diagnostic
                )
            raise RuntimeError("Actual native VPN operation failed; sanitized diagnostic saved")
        if b"RAMPI_RUST_TAILSCALE_ACTION_OK" not in result.stdout:
            raise RuntimeError("Actual native Tailscale adapter result missing")
        return result.stdout.decode()

    run("docker", "network", "create", "--internal", network)
    try:
        run(
            "docker",
            "run",
            "-d",
            "--name",
            coordinator,
            "--network",
            network,
            "--network-alias",
            "login.tailscale.com",
            "--network-alias",
            "controlplane.tailscale.com",
            "--user",
            "root",
            "--memory=512m",
            "--cpus=2",
            "-e",
            "RAMPI_TEST_CONTAINER=1",
            "--mount",
            f"type=bind,source={root.as_posix()},target=/src,readonly",
            args.image,
            "python3",
            "/src/tests/vpn/test-tailscale-live.py",
            "--control",
        )
        for _ in range(200):
            if hs("users", "list", check=False).returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Private Headscale did not start")
        hs("users", "create", "rampi-fixture")
        ca = execute(coordinator, "cat", "/run/rampi-vpn-control/ca.crt").stdout
        logs = []
        original_routes = []
        node_addresses = []
        for index, name in enumerate(peers):
            run(
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--network",
                network,
                "--user",
                "root",
                "--cap-add=NET_ADMIN",
                "--cap-add=NET_RAW",
                "--memory=512m",
                "--cpus=2",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                "--mount",
                f"type=bind,source={root.as_posix()},target=/src,readonly",
                "--mount",
                f"type=volume,source={args.build_volume},target=/build,readonly",
                args.image,
                "python3",
                "/src/tests/vpn/test-tailscale-live.py",
                "--peer",
            )
            execute(
                name,
                "python3",
                "-c",
                "import os,sys; from pathlib import Path; os.umask(0o077); "
                "p=Path('/run/rampi-vpn-ca.tmp'); p.write_bytes(sys.stdin.buffer.read()); "
                "p.rename('/run/rampi-vpn-ca.crt')",
                data=ca,
            )
            for _ in range(200):
                if execute(name, "tailscale", "status", "--json", check=False).stdout.startswith(
                    b"{"
                ):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Private official daemon did not start")
            original_routes.append(
                execute(name, "ip", "-json", "route", "show", "table", "main").stdout
            )
            execute(name, "tailscale", "set", "--operator=rampi")
            # Prepare an existing custom coordination configuration through the
            # official CLI. The Rampi adapter must preserve it, not --reset it.
            execute(
                name,
                "tailscale",
                "up",
                "--login-server=https://login.tailscale.com",
                "--hostname=rampi-peer-" + str(index),
                "--accept-dns=false",
                "--timeout=3s",
                "--json",
                check=False,
                timeout=15,
            )
            logs.append(action(name, "action-login"))
            current = status(name)
            url = current.get("AuthURL", "")
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme != "https" or parsed.netloc != "login.tailscale.com":
                raise RuntimeError(
                    "Real coordinator login URL does not pass the production origin policy"
                )
            auth_id = parsed.path.rstrip("/").rsplit("/", 1)[-1]
            if not auth_id or parsed.query or parsed.fragment:
                raise RuntimeError("Unexpected actual registration URL")
            capabilities.extend([url, auth_id])
            registered = hs(
                "auth", "register", "--auth-id", auth_id, "--user", "rampi-fixture", check=False
            )
            if registered.returncode:
                diagnostic = (registered.stdout + registered.stderr).decode(errors="replace")
                for capability in capabilities:
                    diagnostic = diagnostic.replace(capability, "<private-registration-redacted>")
                (output / "registration-error.log").write_text(diagnostic)
                raise RuntimeError(
                    "Actual coordinator registration failed; sanitized diagnostic saved"
                )
            for _ in range(100):
                current = status(name)
                if current.get("BackendState") == "Running" and current.get("TailscaleIPs"):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("Real enrollment did not reach Running")
            # Tailscale can create a new preference profile on initial login.
            # Admin permission must apply to that actual enrolled profile, using
            # the same official command exposed by the product's setup action.
            prefs = json.loads(execute(name, "tailscale", "debug", "prefs").stdout)
            needed = prefs.get("OperatorUser") != "rampi"
            if needed:
                execute(name, "tailscale", "set", "--operator=rampi")
            prefs = json.loads(execute(name, "tailscale", "debug", "prefs").stdout)
            if prefs.get("OperatorUser") != "rampi":
                raise RuntimeError(
                    "Actual enrolled profile did not accept administrator assignment"
                )
            profile_operator_setup.append(needed)
            preferences.append({key: prefs.get(key) for key in preference_keys})
            node_addresses.append(next(ip for ip in current["TailscaleIPs"] if ":" not in ip))
        for source, destination in [(0, 1), (1, 0)]:
            # Running precedes delivery of the peer map. Require actual kernel
            # traffic within a bounded settling period before measuring it.
            deadline = time.monotonic() + 40
            while execute(
                peers[source], "ping", "-c", "1", "-W", "2",
                node_addresses[destination], check=False,
            ).returncode:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Enrolled peers did not carry actual kernel traffic")
                time.sleep(0.5)
            result = execute(
                peers[source], "ping", "-c", "2", "-W", "3", node_addresses[destination]
            )
            (output / f"icmp-{source}-{destination}.log").write_bytes(result.stdout)
        logs.append(action(peers[0], "action-denied-down", user="vpn-other"))
        denied = execute(peers[0], "tailscale", "down", user="vpn-other", check=False)
        if denied.returncode == 0 or b"Access denied" not in denied.stderr:
            raise RuntimeError("Official daemon did not explicitly deny the unrelated UID")
        (output / "other-user-denied.log").write_bytes(denied.stderr)
        if status(peers[0])["BackendState"] != "Running":
            raise RuntimeError("Another Linux user changed the global VPN")
        logs.append(action(peers[0], "action-down"))
        blocked = execute(
            peers[1], "ping", "-c", "1", "-W", "2", node_addresses[0], check=False
        )
        (output / "icmp-disconnected.log").write_bytes(blocked.stdout)
        if blocked.returncode == 0:
            raise RuntimeError("Tailscale tunnel still carried traffic after disconnect")
        logs.append(action(peers[0], "action-up"))
        restored = execute(peers[1], "ping", "-c", "2", "-W", "3", node_addresses[0])
        (output / "icmp-reconnected.log").write_bytes(restored.stdout)
        for index, name in enumerate(peers):
            prefs = json.loads(execute(name, "tailscale", "debug", "prefs").stdout)
            if {key: prefs.get(key) for key in preference_keys} != preferences[index]:
                raise RuntimeError("VPN operation changed existing official preferences")
            if (
                execute(name, "ip", "-json", "route", "show", "table", "main").stdout
                != original_routes[index]
            ):
                raise RuntimeError("VPN test changed unrelated main-table routes")
        (output / "native-tailscale.log").write_text("".join(logs))
        actual_binary = execute(peers[0], "cat", PROGRAM).stdout
        actual_client = execute(peers[0], "tailscale", "version", "--json").stdout
        actual_control = hs("version").stdout
        (output / "environment.json").write_text(
            json.dumps(
                {
                    "control_server_version": actual_control.decode().strip(),
                    "client_version": json.loads(actual_client),
                    "native_binary_sha256": hashlib.sha256(actual_binary).hexdigest(),
                    "public_provider_oauth_tested": False,
                    "private_dns_aliases": True,
                    "private_network": True,
                    "published_ports": False,
                    "physical_devices": False,
                    "userspace_fake_tunnel": False,
                    "actual_kernel_tun": True,
                    "enrolled_nodes": 2,
                    "bidirectional_icmp": True,
                    "down_blocks_traffic": True,
                    "reconnect_restores_traffic": True,
                    "other_user_change_denied": True,
                    "initial_login_required_profile_operator_assignment": profile_operator_setup,
                    "unrelated_routes_preserved": True,
                    "existing_preferences_preserved": True,
                },
                indent=2,
            )
            + "\n"
        )
        print("RAMPI_NATIVE_TAILSCALE_REAL_TUNNEL_OK")
    finally:
        for name in [*peers, coordinator]:
            result = run("docker", "logs", name, check=False)
            public = (result.stdout + result.stderr).decode(errors="replace")
            if name in peers:
                diagnostic = execute(
                    name, "cat", "/run/rampi-tailscaled.log", check=False
                )
                public += diagnostic.stdout.decode(errors="replace")
                routes = execute(name, "ip", "-json", "route", "show", "table", "all", check=False)
                public += "\nKernel routes:\n" + routes.stdout.decode(errors="replace")
            for capability in capabilities:
                public = public.replace(capability, "<private-registration-redacted>")
            public = re.sub(
                r"https://login[.]tailscale[.]com/register/[^\s\"']+",
                "<private-registration-redacted>",
                public,
            )
            (output / (name + ".log")).write_text(public)
            run("docker", "rm", "-f", name, check=False)
        run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--peer", action="store_true")
    parser.add_argument("--image", default="rampi-complete-vpn-fixture")
    parser.add_argument("--build-volume", default="rampi-rust-build")
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/tailscale-live"))
    options = parser.parse_args()
    if options.control:
        control()
    elif options.peer:
        peer()
    else:
        integration(options)
