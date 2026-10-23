"""Use an actual isolated OpenSSH server to test the GTK host-key trust workflow."""

import os
import subprocess
import tempfile
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable test container required")

with tempfile.TemporaryDirectory(prefix="rampi-ssh-server-") as directory:
    root = Path(directory)
    key = root / "host_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    fingerprint = subprocess.check_output(
        ["ssh-keygen", "-l", "-E", "sha256", "-f", str(key)], text=True
    ).split()[1]
    config = root / "sshd_config"
    config.write_text(
        f"ListenAddress 127.0.0.1\nPort 22222\nHostKey {key}\nPidFile {root}/sshd.pid\n"
        "UsePAM no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n",
        encoding="utf-8",
    )
    log = (root / "sshd.log").open("w")
    server = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e", "-f", str(config)], stderr=log)
    try:
        result = subprocess.run(
            ["/build/target/debug/rampi-native", "--ssh-setup-check"],
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **os.environ,
                "RAMPI_TEST_SSH_FINGERPRINT": fingerprint,
                "RAMPI_TEST_SSH_PUBLIC_KEY": key.with_suffix(".pub").read_text().strip(),
            },
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        assert server.poll() is None
        print(result.stdout.strip())
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
print("PASS: actual OpenSSH host-key exchange and explicit fingerprint trust; no login proof.")
