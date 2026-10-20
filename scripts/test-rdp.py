"""FreeRDP TLS, actual desktop frames, keyboard and reconnect in private Docker."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path


def run(*args: str, input_text: str | None = None, check: bool = True):
    result = subprocess.run(
        args,
        input=input_text.encode("utf-8") if input_text is not None else None,
        capture_output=True,
        timeout=60,
        check=False,
    )
    decoded = subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )
    if check and decoded.returncode:
        raise RuntimeError(
            f"{args[0]} failed (exit {decoded.returncode}): {decoded.stderr[-2000:]}"
        )
    return decoded


def container_only():
    if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
        raise SystemExit("This integration fixture requires its designated disposable container")


def server():
    import grp

    container_only()
    Path("/run/rampi-test-fixture").touch()
    run("useradd", "--create-home", "rdpuser")
    Path("/run/dbus").mkdir(parents=True, exist_ok=True)
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
        "/CN=rampi-rdp.test",
        "-keyout",
        "/etc/xrdp/key.pem",
        "-out",
        "/etc/xrdp/cert.pem",
    )
    os.chown("/etc/xrdp/key.pem", 0, grp.getgrnam("ssl-cert").gr_gid)
    Path("/etc/xrdp/key.pem").chmod(0o640)
    run("usermod", "-a", "-G", "ssl-cert", "xrdp")
    configuration = Path("/etc/xrdp/xrdp.ini")
    configuration.write_text(
        configuration.read_text().replace("security_layer=negotiate", "security_layer=tls")
    )
    Path("/etc/xrdp/startwm.sh").write_text(
        "#!/bin/sh\nopenbox >/home/rdpuser/openbox.log 2>&1 &\nsleep 0.5\n"
        "xsetroot -solid '#267bbd'\n"
        "exec xterm -T RAMPI_SERVER_PROOF -geometry 60x12+100+100 "
        "-e sh -c 'exec python3 /app/scripts/test-rdp.py --fixture "
        "2>/home/rdpuser/fixture-error.log'\n"
    )
    Path("/etc/xrdp/startwm.sh").chmod(0o755)
    Path("/run/xrdp").mkdir(exist_ok=True)
    with subprocess.Popen(["xrdp-sesman", "--nodaemon"]) as sessions:
        try:
            subprocess.run(["xrdp", "--nodaemon"], check=True)
        finally:
            sessions.terminate()


def fixture():
    # sesman intentionally sanitizes the Docker process environment at PAM login.
    if not Path("/.dockerenv").exists() or not Path("/run/rampi-test-fixture").exists():
        raise SystemExit("Missing disposable server fixture marker")
    os.umask(0o077)
    Path.home().joinpath(".rampi-ready").write_text(str(os.getuid()))
    print("RAMPI: actual authenticated remote desktop", flush=True)
    for line in sys.stdin:
        Path.home().joinpath(".rampi-input").write_text(line.strip())
        print("Received keyboard input", flush=True)


def client(address: str, fingerprint: str, token: str, bad_certificate: bool):
    container_only()
    from rampi.config import Host
    from rampi.launch import rdp_args

    password = sys.stdin.readline().strip()
    args = rdp_args(Host(address=address, username="rdpuser"))
    args[args.index("/cert:tofu")] = "/cert:fingerprint:sha256:" + fingerprint
    args += ["/from-stdin:force", "/sec:tls", "/t:RAMPI_RDP_TEST", "/log-level:ERROR"]
    log_path = Path.home() / "rdp-client.log"
    log = log_path.open("wb")
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=log, stderr=log)
    if process.stdin is None:
        raise RuntimeError("No private credentials pipe")
    process.stdin.write((password + "\n").encode())
    process.stdin.close()
    try:
        if bad_certificate:
            if process.wait(timeout=15) == 0:
                raise RuntimeError("FreeRDP accepted an incorrect certificate fingerprint")
            return
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication([])
        matched = False
        for _attempt in range(160):
            app.processEvents()
            if process.poll() is not None:
                raise RuntimeError("FreeRDP exited: " + log_path.read_text(errors="replace")[:2000])
            screen = app.primaryScreen()
            if screen is not None:
                frame = screen.grabWindow(0).toImage()
                if not frame.isNull():
                    color = frame.pixelColor(20, 700)
                    terminal_color = frame.pixelColor(150, 160)
                    if (
                        max(
                            abs(a - b)
                            for a, b in zip(color.getRgb()[:3], (38, 123, 189), strict=True)
                        )
                        < 5 and terminal_color != color
                    ):
                        frame.save(str(Path.home() / "rdp-frame.png"))
                        matched = True
                        break
            time.sleep(0.25)
        if not matched:
            raise RuntimeError("The real remote desktop pixels did not reach the client")
        windows = run(
            "xdotool", "search", "--onlyvisible", "--class", "FreeRDP"
        ).stdout.splitlines()
        run("xdotool", "windowfocus", "--sync", windows[0])
        run("xdotool", "mousemove", "150", "160", "click", "1")
        run("xdotool", "type", "--clearmodifiers", "--delay", "20", token)
        run("xdotool", "key", "Return")
        time.sleep(1)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=8)
        log.close()


def integration(image: str):
    import json

    network = ""
    containers = []
    suffix = uuid.uuid4().hex[:12]
    mount = f"type=bind,source={Path(__file__).resolve().parents[1]},target=/app,readonly"

    def execute(name, *args, input_text=None, check=True):
        return run("docker", "exec", "-i", name, *args, input_text=input_text, check=check)

    try:
        network = run(
            "docker", "network", "create", "--internal", f"rampi-rdp-{suffix}"
        ).stdout.strip()
        for role in ["server", "client"]:
            args = [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--network",
                network,
                "--name",
                f"rampi-rdp-{suffix}-{role}",
                "--memory=512m",
                "--cpus=2",
                "--mount",
                mount,
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                "-e",
                "DISPLAY=:99",
                "-e",
                "QT_QPA_PLATFORM=xcb",
            ]
            if role == "server":
                args += ["--user", "root"]
            args += [image]
            args += (
                ["python3", "-u", "scripts/test-rdp.py", "--server"]
                if role == "server"
                else ["sleep", "infinity"]
            )
            containers.append(run(*args).stdout.strip())
        server_id, client_id = containers
        password = uuid.uuid4().hex + "-Aa7!"
        for _attempt in range(60):
            if execute(server_id, "getent", "passwd", "rdpuser", check=False).returncode == 0:
                break
            time.sleep(0.25)
        execute(server_id, "chpasswd", input_text=f"rdpuser:{password}\n")
        # The image already contains Debian's snakeoil certificate. Wait until our
        # server has replaced it and is listening before reading the fingerprint.
        for _attempt in range(120):
            if ":3389" in execute(server_id, "ss", "-ltn", check=False).stdout:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("The isolated RDP server did not become ready")
        # Certificate material is generated in the fixture, never accepted blindly.
        for _attempt in range(60):
            certificate = execute(
                server_id,
                "openssl",
                "x509",
                "-in",
                "/etc/xrdp/cert.pem",
                "-noout",
                "-fingerprint",
                "-sha256",
                check=False,
            )
            if certificate.returncode == 0:
                break
            time.sleep(0.25)
        fingerprint = certificate.stdout.strip().split("=", 1)[1].replace(":", "")
        address = next(
            iter(
                json.loads(run("docker", "inspect", server_id).stdout)[0]["NetworkSettings"][
                    "Networks"
                ].values()
            )
        )["IPAddress"]
        run(
            "docker",
            "exec",
            "--detach",
            client_id,
            "Xvfb",
            ":99",
            "-screen",
            "0",
            "1024x768x24",
            "-nolisten",
            "tcp",
        )
        time.sleep(1)
        for _cycle in range(2):
            token = "RAMPI_TYPED_" + uuid.uuid4().hex
            execute(
                client_id,
                "python3",
                "scripts/test-rdp.py",
                "--client",
                address,
                "--fingerprint",
                fingerprint,
                "--token",
                token,
                input_text=password + "\n",
            )
            for _attempt in range(30):
                received = execute(server_id, "cat", "/home/rdpuser/.rampi-input", check=False)
                if received.stdout.strip() == token:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Keyboard events did not reach the authenticated remote user")
        execute(
            client_id,
            "python3",
            "scripts/test-rdp.py",
            "--client",
            address,
            "--fingerprint",
            "00" * 32,
            "--bad-certificate",
            input_text=password + "\n",
        )
        print(
            "PASS: actual FreeRDP TLS desktop frames and keyboard roundtrip, reconnect, "
            "and wrong-certificate rejection against isolated xrdp/PAM. Not a Windows NLA test."
        )
    except Exception:
        diagnostics = Path(__file__).resolve().parents[1] / "artifacts/rdp-diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        for container in containers:
            for filename in ["/var/log/xrdp.log", "/var/log/xrdp-sesman.log",
                             "/home/rdpuser/.xsession-errors", "/home/rdpuser/openbox.log",
                             "/home/rdpuser/.rampi-ready", "/home/rdpuser/fixture-error.log",
                             "/home/rampi/rdp-client.log"]:
                output = execute(container, "cat", filename, check=False)
                if output.returncode == 0:
                    (diagnostics / (container[:12] + "-" + Path(filename).name)).write_text(
                        output.stdout
                    )
        raise
    finally:
        for container in containers:
            run("docker", "rm", "--force", container, check=False)
        if network:
            run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="rampi-remote-test")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--client")
    parser.add_argument("--fingerprint", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--bad-certificate", action="store_true")
    options = parser.parse_args()
    if options.server:
        server()
    elif options.fixture:
        fixture()
    elif options.client:
        client(options.client, options.fingerprint, options.token, options.bad_certificate)
    else:
        integration(options.image)
