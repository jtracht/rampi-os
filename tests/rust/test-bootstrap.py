"""Real HTTPS/download/archive checks; installer stub is separate from ARM64 lifecycle."""

import hashlib
import http.server
import io
import os
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable test container required")
if os.geteuid() != 0:
    raise SystemExit("Root is required only for this disposable TLS fixture")

VERSION = "0.6.0-dev.1"
REVISION = "abcde" * 8
SOURCE = f"rampi-source-{VERSION}.tar.gz"
BUNDLE = f"rampi-linux-arm64-{VERSION}.tar.xz"
payload = b"Synthetic binary; real ARM64 installation has its own acceptance.\n"


def archive(entries, mode):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode=mode) as result:
        for name, data, kind in entries:
            item = tarfile.TarInfo(name)
            item.mode = 0o755 if name.endswith(".sh") else 0o644
            item.size = len(data)
            if kind == "link":
                item.type = tarfile.SYMTYPE
                item.linkname = "/etc/rampi-bootstrap-unexpected"
                item.size = 0
            result.addfile(item, io.BytesIO(data) if item.isfile() else None)
    return stream.getvalue()


source = archive(
    [
        ("rampi-os/source-revision.txt", REVISION.encode(), "file"),
        (
            "rampi-os/installer/raspberrypi/setup.sh",
            b'#!/bin/bash\nset -eu\ntest "$1" = --check\n'
            b'test -f "$(dirname "$0")/../../native/bin/rampi-native"\n'
            b'printf verified > "$RAMPI_BOOTSTRAP_TEST_MARKER"\n',
            "file",
        ),
    ],
    "w:gz",
)

with tempfile.TemporaryDirectory(prefix="rampi-bootstrap-tls-") as temporary:
    root = Path(temporary)
    root.chmod(0o755)
    own = root / "personal"
    own.mkdir(mode=0o700)
    os.chown(own, 1000, 1000)
    entry = root / "setup.sh"
    shutil.copyfile("setup.sh", entry)
    marker = own / "installer-entered"
    key, cert = root / "key.pem", root / "cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=Rampi isolated bootstrap fixture",
            "-addext",
            "subjectAltName=DNS:github.com",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    Path("/usr/local/share/ca-certificates/rampi-bootstrap-test.crt").write_bytes(cert.read_bytes())
    subprocess.run(["update-ca-certificates"], check=True, capture_output=True)
    with Path("/etc/hosts").open("a") as hosts:
        hosts.write("\n127.0.0.1 github.com\n")
    files = {}
    paths = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            prefix = f"/jtracht/rampi-os/releases/download/v{VERSION}/"
            name = self.path.removeprefix(prefix)
            if not self.path.startswith(prefix) or name not in files:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(files[name])))
            self.end_headers()
            self.wfile.write(files[name])

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for case in ["valid", "checksum", "revision", "traversal", "link", "duplicate"]:
            entries = [
                ("bin/rampi-native", payload, "file"),
                (
                    "bin/source-revision.txt",
                    ("f" * 40 if case == "revision" else REVISION).encode(),
                    "file",
                ),
                ("bin/binary-sha256.txt", hashlib.sha256(payload).hexdigest().encode(), "file"),
            ]
            if case == "traversal":
                entries.append(("bin/../unexpected", b"no", "file"))
            if case == "link":
                entries.append(("bin/unexpected", b"", "link"))
            if case == "duplicate":
                entries.append(entries[0])
            bundle = archive(entries, "w:xz")
            files.update({SOURCE: source, BUNDLE: bundle})
            files["SHA256SUMS"] = "".join(
                f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n" for name in [SOURCE, BUNDLE]
            ).encode()
            if case == "checksum":
                files[BUNDLE] = bundle + b"modified"
            marker.unlink(missing_ok=True)
            paths.clear()
            result = subprocess.run(
                [
                    "runuser",
                    "-u",
                    "rampi",
                    "--",
                    "env",
                    f"RAMPI_VERSION={VERSION}",
                    f"RAMPI_BOOTSTRAP_TEST_MARKER={marker}",
                    "NO_PROXY=github.com",
                    "bash",
                    str(entry),
                    "--check",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if case == "valid":
                assert result.returncode == 0, result.stdout + result.stderr
                assert marker.read_text() == "verified"
            else:
                assert result.returncode != 0 and not marker.exists(), case
            assert len(paths) == 3 and all(f"/v{VERSION}/" in path for path in paths)
        print("RAMPI_RUST_BOOTSTRAP_TLS_OK")
        print(
            "PASS: actual curl HTTPS, matching source/binary, checksum and archive rejection; "
            "installer stub only."
        )
    finally:
        server.shutdown()
        server.server_close()
