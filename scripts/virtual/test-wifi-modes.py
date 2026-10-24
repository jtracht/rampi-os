"""Actual WPA3-only and hidden SAE with the production Rust/NM adapter in QEMU."""

import os
import subprocess
import time
from pathlib import Path

if os.geteuid() != 0 or not Path("/etc/rampi-acceptance-vm").is_file():
    raise SystemExit("Designated disposable QEMU guest required")
subprocess.run(["systemd-detect-virt", "--vm", "--quiet"], check=True)
root = Path("/run/rampi-acceptance-root")
config = root / "hostapd.conf"
pidfile = root / "hostapd.pid"
original = config.read_text()
binary = "/opt/rampi-source/rampi-network-acceptance"


def run(*args, timeout=180):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Test command {args[0]} failed: " + result.stderr[-2000:])
    return result.stdout


for ssid, option, hidden in [
    ("RampiVirtualSae", "--sae", False),
    ("RampiVirtualHidden", "--hidden-sae", True),
]:
    run("nmcli", "device", "disconnect", "wlan0")
    pid = int(pidfile.read_text().strip())
    if pid <= 1 or Path(f"/proc/{pid}/comm").read_text().strip() != "hostapd":
        raise RuntimeError("Unexpected test access-point process")
    os.kill(pid, 15)
    for _ in range(100):
        if not pidfile.exists():
            break
        time.sleep(0.05)
    text = original.replace("ssid=RampiVirtualPrivate", "ssid=" + ssid).replace(
        "wpa_key_mgmt=WPA-PSK", "wpa_key_mgmt=SAE\nieee80211w=2\nsae_pwe=2"
    )
    if hidden:
        text += "ignore_broadcast_ssid=1\n"
    config.write_text(text)
    config.chmod(0o600)
    run("ip", "netns", "exec", "rampi-ap", "hostapd", "-B", "-P", str(pidfile), str(config))
    print(run("runuser", "-u", "rampi", "--", binary, option), end="", flush=True)
    print(run("runuser", "-u", "rampi-other", "--", binary, "--other", option), end="", flush=True)
print("RAMPI_WPA3_VISIBLE_HIDDEN_MODES_OK", flush=True)
