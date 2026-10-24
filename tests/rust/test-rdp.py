"""Real embedded Rust/Wayland RDP, TLS pin rejection and server keyboard receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
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
    if options.soak:
        Path("/run/rampi-rdp-soak").touch()
    Path("/run/rampi-rdp-probe").write_text(uuid.uuid4().hex)
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
    if options.debug:
        ini.write_text(ini.read_text().replace("LogLevel=INFO", "LogLevel=DEBUG"))
    desktop = (
        "xterm -fa 'DejaVu Sans Mono' -fs 14 -geometry 190x65+0+0 "
        "-e python3 /src/tests/rust/test-rdp.py --fixture"
        if options.soak
        else "python3 /src/tests/rust/test-rdp.py --desktop-fixture"
    )
    Path("/etc/xrdp/startwm.sh").write_text(
        f"#!/bin/sh\nxsetroot -solid '#267bbd'\nexec {desktop} >/home/rdpuser/desktop.log 2>&1\n"
    )
    Path("/etc/xrdp/startwm.sh").chmod(0o755)
    Path("/run/xrdp").mkdir(exist_ok=True)
    # The package already supplies cert.pem. Its existence does not mean the
    # fresh per-test certificate above has been generated and configured yet.
    Path("/run/rampi-rdp-server-ready").touch()
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
    if Path("/run/rampi-rdp-soak").is_file():

        def update_frames():
            # Hide the terminal cursor: frame differences must come from remote
            # content, not a client-side cursor blink.
            print("\033[?25l", end="", flush=True)
            for counter in range(4000):
                print(f"\0337\033[3;1HActual remote frame {counter:06}\0338", end="", flush=True)
                time.sleep(0.25)

        threading.Thread(target=update_frames, daemon=True).start()
    for line in sys.stdin:
        with Path.home().joinpath(".rampi-input").open("a") as receipt:
            receipt.write(line)
        print("Received keyboard input", flush=True)


def desktop_fixture():
    """Ordinary X11 application on the actual XRDP host; no RDP implementation."""
    import tkinter as tk

    if not Path("/run/rampi-rdp-fixture").exists():
        raise SystemExit("Missing disposable server fixture marker")
    os.umask(0o077)
    nonce = Path("/run/rampi-rdp-probe").read_text().strip()
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    root.configure(background="#267bbd")
    tk.Label(
        root,
        text="Actual XRDP desktop · mouse, keyboard and clipboard",
        background="#267bbd",
        foreground="white",
        font=("DejaVu Sans", 22),
    ).pack(pady=24)
    entry = tk.Entry(root, font=("DejaVu Sans Mono", 18))
    entry.pack(fill="x", padx=30)
    tk.Label(
        root,
        text="Remote input receipts are recorded on this server.",
        background="#267bbd",
        foreground="white",
        font=("DejaVu Sans", 18),
    ).pack(pady=80)

    def record(value):
        with Path.home().joinpath(".rampi-events.jsonl").open("a", encoding="utf-8") as receipt:
            receipt.write(json.dumps(value, ensure_ascii=False) + "\n")

    def submit(_event):
        with Path.home().joinpath(".rampi-input").open("a") as receipt:
            receipt.write(entry.get() + "\n")
        entry.delete(0, "end")
        return "break"

    entry.bind("<Return>", submit)
    root.bind("<KeyPress>", lambda e: record({"kind": "key", "key": e.keysym, "state": e.state}))
    root.bind(
        "<ButtonPress>",
        lambda e: record(
            {"kind": "press", "button": e.num, "x": e.x_root, "y": e.y_root, "state": e.state}
        ),
    )
    root.bind(
        "<ButtonRelease>",
        lambda e: (
            record({"kind": "release", "button": e.num, "state": e.state}),
            entry.focus_force(),
        ),
    )
    root.bind("<Motion>", lambda e: record({"kind": "motion", "x": e.x_root, "y": e.y_root}))
    root.after(200, entry.focus_force)

    roundtrip = 0

    def clipboard():
        nonlocal roundtrip
        try:
            text = root.clipboard_get().replace("\r\n", "\n")
        except tk.TclError:
            text = ""
        if text == f"rampi-local-{nonce}-{roundtrip}-Grüße 🥧\nsecond line":
            record({"kind": "clipboard", "text": text})
            root.clipboard_clear()
            root.clipboard_append(f"rampi-remote-{nonce}-{roundtrip}-Grüße 🥧\nsecond line")
            root.update_idletasks()
            roundtrip += 1
        if roundtrip < 2:
            root.after(100, clipboard)

    root.after(100, clipboard)
    root.mainloop()


def client():
    isolated()
    web_server = None
    if options.soak:
        ready = Path("/run/rampi-browser-ready")
        ready.unlink(missing_ok=True)
        web_server = subprocess.Popen(
            ["python3", "/src/tests/rust/test-browser.py", "--serve-only"]
        )
        for _ in range(300):
            if ready.is_file():
                break
            if web_server.poll() is not None:
                raise RuntimeError("Disposable HTTPS fixture exited")
            time.sleep(0.1)
        else:
            web_server.terminate()
            raise RuntimeError("Disposable HTTPS fixture did not become ready")
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
    mode = " --mixed-soak-check" if options.soak else ""
    prefix += (
        f"\ntimeout {800 if options.soak else 160} "
        f"/build/target/debug/rampi-native --rdp-ui-check{mode}\n"
    )
    try:
        subprocess.run(
            ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", "-c", prefix],
            env=environment,
            check=True,
        )
        if run("pgrep", "-x", "Xorg", check=False).returncode == 0:
            raise RuntimeError("X11 was started in the client container")
    finally:
        if web_server is not None:
            web_server.terminate()
            web_server.wait(timeout=5)
        path.unlink(missing_ok=True)
        captured = Path(os.environ["RAMPI_TEST_ARTIFACTS"])
        (captured / "rdp-disconnect-ready").unlink(missing_ok=True)
        # GTK runs as the disposable user with umask 077. Publish only these
        # generated, non-secret test outputs for the host checker/uploader.
        for filename in ("rust-rdp.png", "mixed-remote.png", "rdp-input.json"):
            output = captured / filename
            if output.is_file():
                output.chmod(0o644)


def orchestrate(args):
    root = Path(__file__).resolve().parents[2]
    artifacts = Path(args.artifacts).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    for generated in [
        "rdp-input.json",
        "remote-events.jsonl",
        "channels.log",
        "keyboard-receipts.txt",
        "rust-rdp.png",
    ]:
        (artifacts / generated).unlink(missing_ok=True)
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
            *(["--debug"] if args.debug else []),
            *(["--soak"] if args.soak else []),
        )
        for _ in range(100):
            ready = run(
                "docker", "exec", name, "test", "-f", "/run/rampi-rdp-server-ready", check=False
            )
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("RDP fixture did not finish certificate setup")
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
        probe = run("docker", "exec", name, "cat", "/run/rampi-rdp-probe").stdout.decode().strip()
        credentials = json.dumps(
            {"password": password, "fingerprint": hashlib.sha256(der).hexdigest(), "probe": probe}
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
            *(["--soak"] if args.soak else []),
        ]
        if args.soak:
            command[3:3] = [
                "--security-opt",
                "seccomp=unconfined",
                "--security-opt",
                "apparmor=unconfined",
                "--security-opt",
                "systempaths=unconfined",
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
            result = run(*command, data=credentials, check=False, timeout=850 if args.soak else 190)
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
        receipt_path.chmod(0o644)
        for attempt in range(2):
            if f"rampirdp{attempt}" not in receipt:
                raise RuntimeError(f"Actual remote keyboard receipt missing: {attempt}")
        if not args.soak:
            if "rampiafterhome" not in receipt.splitlines():
                raise RuntimeError("Keyboard did not recover after the reserved dashboard shortcut")
            events_path = artifacts / "remote-events.jsonl"
            run("docker", "cp", f"{name}:/home/rdpuser/.rampi-events.jsonl", str(events_path))
            events_path.chmod(0o644)
            events = [
                json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            for kind in ["press", "release"]:
                if not {1, 2, 3}.issubset({e.get("button") for e in events if e["kind"] == kind}):
                    raise RuntimeError("Actual three-button remote mouse receipts missing: " + kind)
            motions = {(e["x"], e["y"]) for e in events if e["kind"] == "motion"}
            if len(motions) < 2:
                raise RuntimeError("Actual remote pointer motion receipts missing")
            if any(e["kind"] == "key" and e["key"] == "Home" for e in events):
                raise RuntimeError("Reserved Rampi Home shortcut leaked to the remote desktop")
            expected = {
                f"rampi-local-{probe}-{roundtrip}-Grüße 🥧\nsecond line" for roundtrip in range(2)
            }
            if not expected.issubset({e["text"] for e in events if e["kind"] == "clipboard"}):
                raise RuntimeError("Actual remote Unicode clipboard receipts missing")
            print("RAMPI_RUST_RDP_MOUSE_CLIPBOARD_RECEIPTS_OK")
            runpy.run_path(str(root / "scripts/check-rdp-input-evidence.py"))["check"](artifacts)
        if args.soak:
            report = json.loads((artifacts / "mixed-soak.json").read_text())
            for token in report["remote_input_tokens"]:
                if token not in receipt.splitlines():
                    raise RuntimeError("Missing server-side mixed workload input: " + token)
            print("RAMPI_MIXED_SOAK_SERVER_RECEIPTS_OK")
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
            "/home/rdpuser/.rampi-events.jsonl",
        ]:
            run(
                "docker",
                "cp",
                f"{name}:{filename}",
                str(
                    artifacts
                    / (
                        "remote-events.jsonl"
                        if filename.endswith(".rampi-events.jsonl")
                        else Path(filename).name
                    )
                ),
                check=False,
            )
        channels = run(
            "docker",
            "exec",
            name,
            "sh",
            "-c",
            "cat /home/rdpuser/.local/share/xrdp/xrdp-chansrv.*.log",
            check=False,
        )
        if channels.returncode == 0:
            (artifacts / "channels.log").write_bytes(channels.stdout)
        run("docker", "rm", "-f", name, check=False)
        run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--desktop-fixture", action="store_true")
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--soak", action="store_true")
    parser.add_argument(
        "--debug", action="store_true", help="Debug logs on the disposable XRDP fixture only"
    )
    parser.add_argument("--image", default="rampi-rust-rdp")
    parser.add_argument("--server-image", default="rampi-rdp-fixture")
    parser.add_argument("--build-volume", default="rampi-rust-build")
    parser.add_argument("--artifacts", default="artifacts/rust-rdp")
    options = parser.parse_args()
    if options.server:
        server()
    elif options.fixture:
        fixture()
    elif options.desktop_fixture:
        desktop_fixture()
    elif options.client:
        client()
    else:
        orchestrate(options)
