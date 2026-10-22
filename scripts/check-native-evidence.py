"""Fail closed if a native run omitted any required executable acceptance stage."""

import json
import math
import struct
import sys
from pathlib import Path

directory = Path(sys.argv[1])
log = (directory / "wayland.log").read_text(encoding="utf-8")
markers = [
    "RAMPI_RUST_UI_OK",
    "RAMPI_RUST_SETUP_HOSTS_OK",
    "RAMPI_RUST_WAYLAND_KEYBOARD_OK",
    "RAMPI_RUST_VTE_PTY_OK",
    "RAMPI_RUST_WEBKIT_DOM_JS_OK",
    "RAMPI_RUST_BLUEZ_PAGE_OK",
    "RAMPI_RUST_PAIRING_AGENT_OK",
    "RAMPI_RUST_KANBAN_PAGE_OK",
    "RAMPI_RUST_VPN_PAGE_OK",
    "RAMPI_RUST_TAILSCALE_PAGE_OK",
    "RAMPI_RUST_SOUND_PCM_OK",
    "RAMPI_RUST_PERFORMANCE_OK",
    "RAMPI_WAYLAND_WITHOUT_X11_OK",
]
missing = [marker for marker in markers if marker not in log]
if missing:
    raise SystemExit("Missing native acceptance stages: " + ", ".join(missing))
if "RAMPI_RUST_NM_CONTRACT_OK" not in (directory / "network-contract.log").read_text():
    raise SystemExit("Rust/GIO NetworkManager contract did not pass")
if "RAMPI_RUST_BLUEZ_CONTRACT_OK" not in (directory / "bluetooth-contract.log").read_text():
    raise SystemExit("Rust/GIO BlueZ contract did not pass")
if "RAMPI_RUST_WIREGUARD_CONTRACT_OK" not in (directory / "wireguard-contract.log").read_text():
    raise SystemExit("Rust/libnm WireGuard import and profile contract did not pass")
if "RAMPI_RUST_WIREGUARD_PEERS_OK" not in (directory / "wireguard-peers.log").read_text():
    raise SystemExit("Actual Rust/NetworkManager WireGuard peer test did not pass")
if "RAMPI_RUST_TAILSCALE_STATUS_OK" not in (directory / "tailscale-status.log").read_text():
    raise SystemExit("Official Tailscale CLI/daemon status test did not pass")
peak = int((directory / "memory-peak-bytes.txt").read_text())
if not 0 < peak <= 1024**3:
    raise SystemExit("Native runtime exceeded its declared 1-GiB memory limit")
performance = json.loads((directory / "performance.json").read_text(encoding="utf-8"))
for key in ["startup_to_observed_paint_ms", "switch_p95_paint_ms", "process_peak_rss_mib"]:
    if not isinstance(performance.get(key), (int, float)) or not math.isfinite(performance[key]):
        raise SystemExit("Missing or invalid measured performance: " + key)
if (
    performance.get("module_switches", 0) < 600
    or not 0 < performance["startup_to_observed_paint_ms"] < 10000
    or not 0 < performance["switch_p95_paint_ms"] < 500
    or not 0 < performance["process_peak_rss_mib"] < 900
):
    raise SystemExit("Sustained software performance budget did not pass")
if "--require-installer" in sys.argv[2:]:
    if "RAMPI_RUST_INSTALLER_LIFECYCLE_OK" not in (
        directory / "installer-lifecycle.log"
    ).read_text(encoding="utf-8"):
        raise SystemExit("Actual ARM64 installer lifecycle did not pass")
with (directory / "rust-wayland-dashboard.png").open("rb") as image:
    header = image.read(24)
if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) != 24:
    raise SystemExit("Actual native screenshot is missing or invalid")
width, height = struct.unpack(">II", header[16:24])
if width < 960 or height < 540:
    raise SystemExit("Actual native screenshot is smaller than the supported interface")
proof = {
    "required_stages": markers,
    "peak_mib": round(peak / 1024**2, 1),
    "screenshot": [width, height],
    "performance": performance,
}
(directory / "native-acceptance.json").write_text(json.dumps(proof, indent=2) + "\n")
print("PASS: every required native stage has executable evidence.")
