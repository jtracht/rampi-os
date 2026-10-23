"""Real embedded Rust/Wayland RDP, TLS pin rejection and server keyboard receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


def run(*args, data=None, check=True, timeout=120):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.decode(errors='replace')[-4000:]}")
    return result


def isolated():
    if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
        raise SystemExit("Only inside the designated disposable container")


def server():
    import grp

    isolated()
    run("useradd", "--create-home", "rdpuser")
    Path("/run/rampi-rdp-fixture").touch()
    Path("/run/dbus").mkdir(exist_ok=True)
    run("dbus-daemon", "--system", "--fork")
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
        "/CN=rdp-server",
        "-keyout",
        "/etc/xrdp/key.pem",
        "-out",
        "/etc/xrdp/cert.pem",
    )
    os.chown("/etc/xrdp/key.pem", 0, grp.getgrnam("ssl-cert").gr_gid)
    Path("/etc/xrdp/key.pem").chmod(0o640)
    run("usermod", "-a", "-G", "ssl-cert", "xrdp")
    ini = Path("/etc/xrdp/xrdp.ini")
    ini.write_text(ini.read_text().replace("security_layer=negotiate", "security_layer=tls"))
    Path("/etc/xrdp/startwm.sh").write_text(
        "#!/bin/sh\nxsetroot -solid '#267bbd'\n"
        "exec xterm -fa 'DejaVu Sans Mono' -fs 14 -geometry 190x65+0+0 "
        "-e python3 /src/tests/rust/test-rdp.py --fixture >/home/rdpuser/desktop.log 2>&1\n"
    )
    Path("/etc/xrdp/startwm.sh").chmod(0o755)
    Path("/run/xrdp").mkdir(exist_ok=True)
    sessions = subprocess.Popen(["xrdp-sesman", "--nodaemon"])
    try:
        subprocess.run(["xrdp", "--nodaemon"], check=True)
    finally:
        sessions.terminate()


def fixture():
    if not Path("/run/rampi-rdp-fixture").exists():
        raise SystemExit("Missing fixture marker")
    os.umask(0o077)
    print("RAMPI: actual TLS authenticated remote desktop", flush=True)
    for line in sys.stdin:
        with Path.home().joinpath(".rampi-input").open("a") as receipt:
            receipt.write(line)
        print("Received keyboard input", flush=True)


def client():
    isolated()
    descriptor, filename = tempfile.mkstemp(prefix="rampi-rdp-")
    os.close(descriptor)
    path = Path(filename)
    path.write_bytes(sys.stdin.buffer.read())
    path.chmod(0o600)
    os.chown(path, 1000, 1000)
    environment = dict(os.environ, RAMPI_TEST_RDP_FILE=str(path))
    prefix = (
        Path("/src/tests/rust/run-wayland.sh")
        .read_text()
        .split("bash tests/rust/test-first-run.sh")[0]
    )
    prefix += "\ntimeout 110 /build/target/debug/rampi-native --rdp-ui-check\n"
    try:
        subprocess.run(
            ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", "-c", prefix],
            env=environment,
            check=True,
        )
        if run("pgrep", "-x", "Xorg", check=False).returncode == 0:
            raise RuntimeError("X11 was started in the client container")
    finally:
        path.unlink(missing_ok=True)


def orchestrate(args):
    root = Path(__file__).resolve().parents[2]
    artifacts = Path(args.artifacts).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    ready_file = artifacts / "rdp-disconnect-ready"
    ready_file.unlink(missing_ok=True)
    suffix = uuid.uuid4().hex[:10]
    network, name = f"rampi-rdp-{suffix}", f"rampi-rdp-server-{suffix}"
    run("docker", "network", "create", "--internal", network)
    try:
        run(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            network,
            "--network-alias",
            "rdp-server",
            "--user",
            "root",
            "--mount",
            f"type=bind,source={root},target=/src,readonly",
            "-e",
            "RAMPI_TEST_CONTAINER=1",
            args.server_image,
            "python3",
            "/src/tests/rust/test-rdp.py",
            "--server",
        )
        for _ in range(100):
            ready = run("docker", "exec", name, "test", "-f", "/etc/xrdp/cert.pem", check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        password = secrets.token_urlsafe(24)
        run("docker", "exec", "-i", name, "chpasswd", data=f"rdpuser:{password}\n".encode())
        der = run(
            "docker",
            "exec",
            name,
            "openssl",
            "x509",
            "-in",
            "/etc/xrdp/cert.pem",
            "-outform",
            "DER",
        ).stdout
        credentials = json.dumps(
            {"password": password, "fingerprint": hashlib.sha256(der).hexdigest()}
        ).encode()
        command = [
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
            "--user",
            "root",
            "--mount",
            f"type=bind,source={root},target=/src,readonly",
            "--mount",
            f"type=bind,source={artifacts},target=/artifacts",
            "--mount",
            f"type=volume,source={args.build_volume},target=/build,readonly",
            "-e",
            "RAMPI_TEST_CONTAINER=1",
            "-e",
            "RAMPI_TEST_ARTIFACTS=/artifacts",
            args.image,
            "python3",
            "/src/tests/rust/test-rdp.py",
            "--client",
        ]
        finished = threading.Event()

        def interrupt_server():
            while not finished.wait(0.1):
                if ready_file.is_file():
                    run("docker", "exec", name, "pkill", "-x", "xrdp", check=False)
                    return

        watcher = threading.Thread(target=interrupt_server)
        watcher.start()
        try:
            result = run(*command, data=credentials, check=False, timeout=140)
        finally:
            finished.set()
            watcher.join(timeout=10)
        log = result.stdout + result.stderr
        (artifacts / "rdp.log").write_bytes(log)
        print(log.decode(errors="replace"))
        if password.encode() in log:
            raise RuntimeError("Password leaked in application log")
        if result.returncode:
            raise RuntimeError(f"Embedded RDP client failed: {result.returncode}")
        receipt_path = artifacts / "keyboard-receipts.txt"
        run("docker", "cp", f"{name}:/home/rdpuser/.rampi-input", str(receipt_path))
        receipt = receipt_path.read_text(encoding="utf-8")
        for attempt in range(2):
            if f"rampirdp{attempt}" not in receipt:
                raise RuntimeError(f"Actual remote keyboard receipt missing: {attempt}")
        if "Gtk-CRITICAL" in log.decode() or "panicked at" in log.decode():
            raise RuntimeError("Native RDP runtime error")
        print("RAMPI_RUST_RDP_SERVER_RECEIPTS_OK")
    finally:
        log = run("docker", "logs", name, check=False)
        (artifacts / "server.log").write_bytes(log.stdout + log.stderr)
        for filename in [
            "/var/log/xrdp.log",
            "/var/log/xrdp-sesman.log",
            "/home/rdpuser/desktop.log",
        ]:
            run(
                "docker",
                "cp",
                f"{name}:{filename}",
                str(artifacts / Path(filename).name),
                check=False,
            )
        run("docker", "rm", "-f", name, check=False)
        run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--image", default="rampi-rust-rdp")
    parser.add_argument("--server-image", default="rampi-rdp-fixture")
    parser.add_argument("--build-volume", default="rampi-rust-build")
    parser.add_argument("--artifacts", default="artifacts/rust-rdp")
    options = parser.parse_args()
    if options.server:
        server()
    elif options.fixture:
        fixture()
    elif options.client:
        client()
    else:
        orchestrate(options)
