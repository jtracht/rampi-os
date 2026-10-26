"""Production Rampi page against FreeRDP/WinPR NLA in private Linux containers.

Uses the packaged server, CredSSP/NTLM implementation and password hashing API.
No Windows machine, published port or replacement authentication protocol.
"""

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path


def run(*arguments, data=None, check=True, timeout=120):
    result = subprocess.run(arguments, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"NLA fixture operation failed: exit {result.returncode}")
    return result


def server():
    if not Path("/.dockerenv").is_file() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
        raise RuntimeError("Only in a designated disposable Linux container")
    os.umask(0o077)
    request = Path("/run/rampi-nla-request.json")
    for _ in range(600):
        if request.is_file():
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Ephemeral NLA fixture credentials were not supplied")
    credential = json.loads(request.read_bytes())
    request.unlink()
    password = credential["password"].encode()
    run("useradd", "--create-home", "--shell", "/bin/bash", "rdpuser")
    run("chpasswd", data=b"rdpuser:" + password + b"\n")
    # WinPR's existing password-hashing implementation; no own crypto, shell
    # interpolation or password in argv. The SAM is private and never exported.
    library = ctypes.CDLL(ctypes.util.find_library("winpr3"))
    initialize_ssl = library.winpr_InitializeSSL
    initialize_ssl.argtypes = (ctypes.c_uint32,)
    initialize_ssl.restype = ctypes.c_int
    if initialize_ssl(0) != 1:  # WINPR_SSL_INIT_DEFAULT, including NTLM's legacy digest provider.
        raise RuntimeError("WinPR could not initialize its crypto providers")
    hash_password = library.NTOWFv1A
    hash_password.argtypes = (ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p)
    hash_password.restype = ctypes.c_int
    digest = ctypes.create_string_buffer(16)
    if hash_password(password, len(password), digest) != 1:
        raise RuntimeError("WinPR could not create its fixture SAM")
    sam = Path("/run/rampi-nla.sam")
    sam.write_text("rdpuser:RAMPI::" + digest.raw.hex() + ":::\n")
    sam.chmod(0o600)
    Path("/run/rampi-rdp-fixture").touch()
    Path("/run/rampi-rdp-probe").write_text(uuid.uuid4().hex)
    Path("/run/rampi-rdp-probe").chmod(0o644)  # Public test nonce for the unprivileged desktop.
    environment = dict(os.environ, DISPLAY=":99")
    display = subprocess.Popen(
        [
            "Xvfb",
            ":99",
            "-screen",
            "0",
            "1280x720x24",
            "-nolisten",
            "tcp",
            "-ac",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    desktop = None
    shadow = None
    try:
        for _ in range(100):
            if run("xdpyinfo", "-display", ":99", check=False).returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("NLA fixture display did not start")
        desktop = subprocess.Popen(
            [
                "runuser",
                "-u",
                "rdpuser",
                "--",
                "env",
                "DISPLAY=:99",
                "python3",
                "/src/tests/rust/test-rdp.py",
                "--desktop-fixture",
            ],
            env=environment,
        )
        shadow = subprocess.Popen(
            [
                "freerdp-shadow-cli3",
                "/port:3389",
                "/sec:nla",
                "/sam-file:" + str(sam),
                "-gfx",
                "-rfx",
                "-nsc",
                "/log-level:INFO",
            ],
            env=environment,
        )
        for _ in range(200):
            if shadow.poll() is not None:
                raise RuntimeError("NLA-only shadow server terminated")
            certificates = list(Path("/root/.config").rglob("shadow.crt"))
            if len(certificates) == 1:
                try:
                    with socket.create_connection(("127.0.0.1", 3389), timeout=1):
                        Path("/run/rampi-nla-cert.pem").write_bytes(certificates[0].read_bytes())
                        Path("/run/rampi-nla-ready").touch()
                        break
                except OSError:
                    pass
            time.sleep(0.1)
        else:
            raise RuntimeError("NLA server/certificate did not become ready")
        shadow.wait()
    finally:
        for process in (shadow, desktop, display):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        sam.unlink(missing_ok=True)


def orchestrate(arguments):
    root = Path(__file__).resolve().parents[2]
    output = arguments.artifacts.resolve()
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o777)
    suffix = uuid.uuid4().hex[:12]
    network, name = "rampi-nla-net-" + suffix, "rampi-nla-server-" + suffix
    password = secrets.token_urlsafe(32)
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
            "--memory=512m",
            "--cpus=2",
            "-e",
            "RAMPI_TEST_CONTAINER=1",
            "--mount",
            f"type=bind,source={root.as_posix()},target=/src,readonly",
            arguments.server_image,
            "python3",
            "/src/tests/rust/test-rdp-nla.py",
            "--server",
        )
        run(
            "docker",
            "exec",
            "-i",
            name,
            "python3",
            "-c",
            "import os,sys; from pathlib import Path; os.umask(0o077); "
            "p=Path('/run/rampi-nla-request.tmp'); p.write_bytes(sys.stdin.buffer.read()); "
            "p.rename('/run/rampi-nla-request.json')",
            data=json.dumps({"password": password}).encode(),
        )
        for _ in range(150):
            if (
                run(
                    "docker", "exec", name, "test", "-f", "/run/rampi-nla-ready", check=False
                ).returncode
                == 0
            ):
                break
            if (
                run(
                    "docker", "inspect", "--format", "{{.State.Running}}", name, check=False
                ).stdout.strip()
                != b"true"
            ):
                raise RuntimeError("Disposable NLA server stopped during startup")
            time.sleep(0.2)
        else:
            raise RuntimeError("Disposable NLA server readiness timed out")
        der = run(
            "docker",
            "exec",
            name,
            "openssl",
            "x509",
            "-in",
            "/run/rampi-nla-cert.pem",
            "-outform",
            "DER",
        ).stdout
        credential = {
            "nla": True,
            "username": "RAMPI\\rdpuser",
            "password": password,
            "fingerprint": hashlib.sha256(der).hexdigest(),
        }
        result = run(
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            network,
            "--memory=1g",
            "--memory-swap=1g",
            "--cpus=4",
            "--user",
            "root",
            "--mount",
            f"type=bind,source={root.as_posix()},target=/src,readonly",
            "--mount",
            f"type=bind,source={output.as_posix()},target=/artifacts",
            "--mount",
            f"type=volume,source={arguments.build_volume},target=/build,readonly",
            "-e",
            "RAMPI_TEST_CONTAINER=1",
            "-e",
            "RAMPI_TEST_ARTIFACTS=/artifacts",
            arguments.image,
            "python3",
            "/src/tests/rust/test-rdp.py",
            "--client",
            data=json.dumps(credential).encode(),
            check=False,
            timeout=280,
        )
        log = result.stdout + result.stderr
        if password.encode() in log:
            raise RuntimeError("NLA password leaked in application output")
        (output / "nla-client.log").write_bytes(log)
        sys.stdout.buffer.write(log)
        if result.returncode or b"RAMPI_RUST_RDP_NLA_DOMAIN_RECONNECT_OK" not in log:
            raise RuntimeError("Actual native NLA authentication failed")
        receipt = run("docker", "exec", name, "cat", "/home/rdpuser/.rampi-input").stdout
        for attempt in (0, 1):
            if f"rampinla{attempt}".encode() not in receipt.splitlines():
                raise RuntimeError("Actual NLA desktop keyboard receipt missing")
        (output / "nla-keyboard-receipts.txt").write_bytes(receipt)
        binary_hash = (
            run(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--mount",
                f"type=volume,source={arguments.build_volume},target=/build,readonly",
                arguments.image,
                "sha256sum",
                "/build/target/debug/rampi-native",
            )
            .stdout.split()[0]
            .decode()
        )
        (output / "nla-environment.json").write_text(
            json.dumps(
                {
                    "windows_host": False,
                    "private_network": True,
                    "published_ports": False,
                    "server": "FreeRDP/WinPR",
                    "security": "nla-only",
                    "domain": "RAMPI",
                    "bad_certificate_rejected": b"RAMPI_RUST_RDP_BAD_CERTIFICATE_OK" in log,
                    "bad_credentials_rejected": b"RAMPI_RUST_RDP_NLA_BAD_ACCOUNT_REJECT_OK" in log,
                    "reconnected": True,
                    "keyboard_receipts": 2,
                    "binary_sha256": binary_hash,
                },
                indent=2,
            )
            + "\n"
        )
        print("RAMPI_RUST_RDP_NLA_SERVER_RECEIPTS_OK")
    finally:
        logs = run("docker", "logs", name, check=False)
        public = logs.stdout + logs.stderr
        if password.encode() not in public:
            (output / "nla-server.log").write_bytes(public)
        run("docker", "rm", "-f", name, check=False)
        run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--image", default="rampi-rust-dev")
    parser.add_argument("--server-image", default="rampi-native-rdp-fixture")
    parser.add_argument("--build-volume", default="rampi-rust-build")
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/rdp-nla"))
    options = parser.parse_args()
    if options.server:
        server()
    else:
        orchestrate(options)
