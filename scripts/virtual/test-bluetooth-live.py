"""Real Rust/GIO + BlueZ + kernel VHCI pairing; no physical device or HID claim."""

import os
import subprocess
import tempfile
import time
from pathlib import Path

if os.geteuid() != 0 or not Path("/etc/rampi-acceptance-vm").is_file():
    raise SystemExit("Designated disposable QEMU guest required")
subprocess.run(["systemd-detect-virt", "--vm", "--quiet"], check=True)


def run(*args):
    return subprocess.check_output(args, text=True, timeout=120)


def property_value(path, interface, name):
    return run("busctl", "get-property", "org.bluez", path, interface, name).strip()


peer = "/org/bluez/hci1"
for key in ["Powered", "Pairable", "Discoverable"]:
    run("busctl", "set-property", "org.bluez", peer, "org.bluez.Adapter1", key, "b", "true")

# The existing official interactive agent supplies the test peer's JustWorks
# capability. Rampi's PIN/passkey UI is covered by its separate Agent1 tests.
with tempfile.NamedTemporaryFile(mode="w+", prefix="rampi-live-agent-") as log:
    agent = subprocess.Popen(
        ["stdbuf", "-oL", "-eL", "bluetoothctl", "--agent", "NoInputNoOutput"],
        stdin=subprocess.PIPE,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        for expected in ["Agent registered", "Default agent request successful"]:
            if expected.startswith("Default"):
                agent.stdin.write("default-agent\n")
                agent.stdin.flush()
            for _ in range(100):
                if expected in Path(log.name).read_text():
                    break
                if agent.poll() is not None:
                    raise RuntimeError("Official BlueZ test peer agent exited")
                time.sleep(0.1)
            else:
                raise RuntimeError(
                    "Official BlueZ agent was not ready: " + Path(log.name).read_text()[-4096:]
                )
        binary = "/opt/rampi-source/rampi-network-acceptance"
        print(run("runuser", "-u", "rampi", "--", binary, "--bluetooth"), end="")
        addresses = [
            property_value("/org/bluez/hci0", "org.bluez.Adapter1", "Address").split('"')[1],
            property_value(peer, "org.bluez.Adapter1", "Address").split('"')[1],
        ]
        # Never print or export link keys. Require actual system bond storage on
        # both sides, rather than accepting only a fabricated paired UI state.
        for local, remote in [addresses, list(reversed(addresses))]:
            info = Path("/var/lib/bluetooth") / local / remote / "info"
            for _ in range(50):
                if info.is_file() and "[LinkKey]" in info.read_text():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Actual peer link-key storage missing")
        print("RAMPI_BLUEZ_VHCI_BOTH_BONDS_OK")
        print(run("runuser", "-u", "rampi", "--", binary, "--bluetooth-cleanup"), end="")
        if (Path("/var/lib/bluetooth") / addresses[0] / addresses[1] / "info").exists():
            raise RuntimeError("Removed peer bond remained stored")
    finally:
        agent.terminate()
        agent.wait(timeout=10)
print(
    "PASS: actual virtual-controller pairing and bond storage, trust removal and power; "
    "no HID/RF proof."
)
