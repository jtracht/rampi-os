"""Official CLI/daemon status plus clearly separate adversarial CLI fixtures.

No login, tailnet enrollment or Tailscale tunnel is claimed by this test.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Requires the disposable test container")

BINARY = "/build/target/debug/rampi-native"
SOCKET = Path("/run/tailscale/tailscaled.sock")
if SOCKET.exists():
    raise SystemExit("An existing Tailscale service is present; refusing to disturb it")


def check(case, **environment):
    result = subprocess.run(
        [BINARY, "--tailscale-check", case],
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode:
        raise RuntimeError(f"Rust Tailscale check failed: {case}; " + result.stderr)
    print(result.stdout.strip())


ui = "--ui" in sys.argv
with tempfile.TemporaryDirectory(prefix="rampi-ts-") as directory:
    root = Path(directory)
    if not ui:
        check("missing", PATH=str(root / "missing"))
        check("unavailable")  # Actual official CLI with no running daemon.
        fixture_bin = root / "bin"
        fixture_bin.mkdir()
        fixture = fixture_bin / "tailscale"
        for case, body in [
            ("invalid", "print('invalid CLI fixture output')"),
            ("oversized", "import sys; sys.stdout.write('x' * 300000); sys.stdout.flush()"),
            (
                "timeout",
                "import os,time; from pathlib import Path; "
                "Path(os.environ['RAMPI_FIXTURE_PID']).write_text(str(os.getpid())); "
                "time.sleep(30)",
            ),
        ]:
            fixture.write_text("#!/usr/bin/python3\n" + body + "\n")
            fixture.chmod(0o700)
            pidfile = root / "fixture.pid"
            started = time.monotonic()
            check(case, PATH=str(fixture_bin), RAMPI_FIXTURE_PID=str(pidfile))
            if case == "timeout":
                assert 4 <= time.monotonic() - started < 12
                try:
                    os.kill(int(pidfile.read_text()), 0)
                except ProcessLookupError:
                    pass
                else:
                    raise RuntimeError("Timed-out CLI fixture was not reaped")

    with (root / "daemon.log").open("w") as output:
        daemon = subprocess.Popen(
            [
                "tailscaled",
                "--tun=userspace-networking",
                f"--state={root / 'state'}",
                f"--statedir={root}",
                f"--socket={SOCKET}",
                "--port=0",
            ],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            ready = False
            for _ in range(100):
                if daemon.poll() is not None:
                    raise RuntimeError("Official isolated Tailscale daemon exited")
                result = subprocess.run(
                    ["tailscale", "status", "--json", "--peers=false"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if result.returncode == 0:
                    state = json.loads(result.stdout).get("BackendState")
                    if state == "NeedsLogin":
                        ready = True
                        break
                time.sleep(0.1)
            if not ready:
                raise RuntimeError("Official Tailscale daemon did not reach NeedsLogin")
            if ui:
                result = subprocess.run(
                    [BINARY, "--tailscale-ui-check"], capture_output=True, text=True, timeout=20
                )
                if result.returncode:
                    raise RuntimeError(result.stderr)
                print(result.stdout.strip())
            else:
                check("needs-login")
                print("RAMPI_RUST_TAILSCALE_STATUS_OK")
        finally:
            daemon.terminate()
            try:
                daemon.wait(timeout=10)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait(timeout=5)

print("PASS: official Tailscale CLI/daemon NeedsLogin status; no authentication or tunnel proof.")
