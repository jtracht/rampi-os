"""Actual trusted TLS, WebKit transfers and inline requests; disposable local CA only."""

import http.server
import os
import ssl
import subprocess
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
    def do_GET(self):
        if self.path == "/download":
            body = b"Rampi actual HTTPS download\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="../fixture.bin"')
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
        prefix = (
            Path("tests/rust/run-wayland.sh")
            .read_text()
            .split("bash tests/rust/test-first-run.sh")[0]
        )
        script = root / "session.sh"
        script.write_text(
            prefix + "timeout 60 /build/target/debug/rampi-native --browser-https-check\n"
        )
        result = subprocess.run(
            ["runuser", "-u", "rampi", "--", "dbus-run-session", "--", "bash", str(script)],
            capture_output=True,
            text=True,
            timeout=70,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        assert "RAMPI_RUST_BROWSER_HTTPS_DOWNLOADS_OK" in result.stdout
        print(result.stdout.strip())
    finally:
        server.shutdown()
        server.server_close()
print(
    "PASS: actual trusted HTTPS, hostname rejection, navigation, inline JavaScript dialogs "
    "and consent-gated WebKit downloads; no external windows."
)
