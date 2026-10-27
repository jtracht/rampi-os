"""Actual trusted TLS, WebKit transfers and inline requests; disposable local CA only."""

import http.server
import os
import ssl
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

if (
    os.environ.get("RAMPI_TEST_CONTAINER") != "1"
    or not Path("/.dockerenv").exists()
    or os.geteuid() != 0
):
    raise SystemExit("Disposable container root required")


def run(*args):
    subprocess.run(args, check=True, capture_output=True)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(min(length, 4096))
        valid = self.path == "/upload" and body == b"Rampi consented upload\n"
        self.send_response(200 if valid else 400)
        self.end_headers()
        self.wfile.write(b"Rampi upload received" if valid else b"Upload mismatch")

    def do_GET(self):
        if self.path == "/soak":
            body = Path("/src/tests/rust/soak.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/download":
            body = b"Rampi actual HTTPS download\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="../fixture.bin"')
        elif self.path == "/modern":
            body = Path(__file__).with_name("browser-modern.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif self.path == "/uploads":
            body = (
                b"<!doctype html><title>Rampi upload fixture</title>"
                b'<input id="single" type="file" accept="text/plain">'
                b'<input id="multiple" type="file" multiple>'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        else:
            title = "Rampi HTTPS second" if self.path == "/second" else "Rampi HTTPS start"
            body = (
                f"<!doctype html><html><head><title>{title}</title></head>"
                f"<body>{title}</body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


with tempfile.TemporaryDirectory(prefix="rampi-browser-") as directory:
    root = Path(directory)
    root.chmod(0o755)
    ca, ca_key, cert, key, csr = [
        str(root / name) for name in ["ca.crt", "ca.key", "server.crt", "server.key", "server.csr"]
    ]
    run(
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
        "/CN=Rampi disposable browser CA",
        "-addext",
        "basicConstraints=critical,CA:TRUE",
    )
    run(
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
        "/CN=localhost",
    )
    extension = root / "extensions"
    extension.write_text(
        "subjectAltName=DNS:localhost\nbasicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\n"
    )
    run(
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
        str(extension),
    )
    Path("/usr/local/share/ca-certificates/rampi-disposable.crt").write_bytes(Path(ca).read_bytes())
    run("update-ca-certificates")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 22225), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        if "--serve-only" in sys.argv:
            Path("/run/rampi-browser-ready").touch()
            threading.Event().wait(900)
            raise SystemExit(0)
        # Normal systemd Linux creates this root-owned shared socket directory.
        # The disposable Docker image has no tmpfiles service.
        x11_directory = Path("/tmp/.X11-unix")  # noqa: S108 - standard OS socket directory
        x11_directory.mkdir(mode=0o1777, exist_ok=True)
        x11_directory.chmod(0o1777)
        os.chown(x11_directory, 0, 0)
        prefix = (
            Path("tests/rust/run-wayland.sh")
            .read_text()
            .split("bash tests/rust/test-first-run.sh")[0]
        )
        script = root / "session.sh"
        script.write_text(
            prefix + "timeout 60 /build/target/debug/rampi-native --browser-https-check\n"
            "timeout 25 /build/target/debug/rampi-native --browser-profile-check\n"
            'printf "RAMPI_BROWSER_PROFILE_DIR=%s\\n" "$XDG_CONFIG_HOME/rampi/browser-native"\n'
        )
        result = subprocess.run(
            ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", str(script)],
            capture_output=True,
            text=True,
            timeout=95,
        )
        if result.returncode or "Gtk-CRITICAL" in result.stderr:
            raise RuntimeError(result.stdout + result.stderr)
        assert "RAMPI_RUST_BROWSER_HTTPS_DOWNLOADS_OK" in result.stdout
        assert "RAMPI_RUST_BROWSER_UPLOAD_CONSENT_OK" in result.stdout
        assert "RAMPI_RUST_BROWSER_DEVICE_CONSENT_MOCK_CAPTURE_OK" in result.stdout
        assert "RAMPI_RUST_BROWSER_MODERN_INPUT_FULLSCREEN_OK" in result.stdout
        assert "RAMPI_RUST_BROWSER_PROFILE_RESTART_OK" in result.stdout
        profile = next(
            line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("RAMPI_BROWSER_PROFILE_DIR=")
        )
        run("useradd", "--create-home", "browser-other")
        forbidden = subprocess.run(
            ["runuser", "-u", "browser-other", "--", "cat", profile + "/cookies.sqlite"],
            capture_output=True,
        )
        if forbidden.returncode == 0:
            raise RuntimeError("Other Linux account could read the browser cookie profile")
        script.write_text(
            prefix + "timeout 25 /build/target/debug/rampi-native --browser-profile-empty-check\n"
        )
        other = subprocess.run(
            ["runuser", "-u", "browser-other", "--", "dbus-run-session", "--", "bash", str(script)],
            capture_output=True,
            text=True,
            timeout=35,
        )
        if other.returncode or "RAMPI_RUST_BROWSER_OTHER_ACCOUNT_EMPTY_OK" not in other.stdout:
            raise RuntimeError(other.stdout + other.stderr)
        print(other.stdout.strip())
        print(result.stdout.strip())
    finally:
        server.shutdown()
        server.server_close()
print(
    "PASS: actual trusted HTTPS, hostname rejection, navigation, inline JavaScript dialogs "
    "and consent-gated WebKit downloads/uploads, multiple selection and navigation cancellation; "
    "no external windows."
)
