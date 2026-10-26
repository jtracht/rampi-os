"""Fail closed if a native run omitted any required executable acceptance stage."""

import json
import math
import runpy
import struct
import sys
from pathlib import Path

directory = Path(sys.argv[1])
if "RAMPI_KEYRING_PROFILE_PRESERVATION_OK" not in (directory / "keyring-profile.log").read_text():
    raise SystemExit("Actual unprivileged keyring profile preservation did not pass")
runpy.run_path(str(Path(__file__).with_name("check-gitea-evidence.py")))["check"](
    directory / "gitea-live"
)
rdp_input = runpy.run_path(str(Path(__file__).with_name("check-rdp-input-evidence.py")))["check"](
    directory
)
runpy.run_path(str(Path(__file__).with_name("check-soak-evidence.py")))["check"](
    directory / "mixed-soak"
)
rdp_log = (directory / "rdp-acceptance.log").read_text(encoding="utf-8")
for marker in [
    "RAMPI_RUST_RDP_BAD_CERTIFICATE_OK",
    "RAMPI_RUST_RDP_EMBEDDED_RECONNECT_OK",
    "RAMPI_RUST_RDP_SERVER_FAILURE_OK",
    "RAMPI_RUST_RDP_SERVER_RECEIPTS_OK",
    "RAMPI_RUST_RDP_MOUSE_CLIPBOARD_OK",
    "RAMPI_RUST_RDP_MOUSE_CLIPBOARD_RECEIPTS_OK",
]:
    if marker not in rdp_log:
        raise SystemExit("Missing actual embedded RDP acceptance: " + marker)
log = (directory / "wayland.log").read_text(encoding="utf-8")
markers = [
    "RAMPI_RUST_FIRST_RUN_KEYBOARD_OK",
    "RAMPI_RUST_UI_OK",
    "RAMPI_RUST_NO_PROVIDER_ROUTES_OK",
    "RAMPI_RUST_THREE_MODULE_NAVIGATION_OK",
    "RAMPI_RUST_SETUP_HOSTS_OK",
    "RAMPI_RUST_SETUP_ALL_ROUTES_OK",
    "RAMPI_RUST_SSH_TRUST_OK",
    "RAMPI_RUST_SSH_AGENT_UNLOCK_OK",
    "RAMPI_RUST_SSH_AGENT_LIFETIME_OK",
    "RAMPI_RUST_DASHBOARD_STATUS_OK",
    "RAMPI_RUST_SYSTEM_SETTINGS_OK",
    "RAMPI_RUST_WAYLAND_KEYBOARD_OK",
    "RAMPI_RUST_VTE_PTY_OK",
    "RAMPI_RUST_WEBKIT_DOM_JS_OK",
    "RAMPI_RUST_BLUEZ_PAGE_OK",
    "RAMPI_RUST_BLUEZ_ADAPTER_SWITCH_OK",
    "RAMPI_RUST_PAIRING_AGENT_OK",
    "RAMPI_RUST_PAIRING_RESTART_OK",
    "RAMPI_RUST_INTERACTION_KEYBOARD_OK",
    "RAMPI_RUST_FOUR_EDGE_VISUAL_OK",
    "RAMPI_RUST_KANBAN_PAGE_OK",
    "RAMPI_RUST_VPN_PAGE_OK",
    "RAMPI_RUST_TAILSCALE_PAGE_OK",
    "RAMPI_RUST_TAILSCALE_ACTION_PAGE_OK",
    "RAMPI_RUST_SOUND_PCM_OK",
    "RAMPI_RUST_PERFORMANCE_OK",
    "RAMPI_WAYLAND_WITHOUT_X11_OK",
]
missing = [marker for marker in markers if marker not in log]
if missing:
    raise SystemExit("Missing native acceptance stages: " + ", ".join(missing))
if "RAMPI_RUST_BOOTSTRAP_TLS_OK" not in (directory / "bootstrap-tls.log").read_text(
    encoding="utf-8"
):
    raise SystemExit("Native HTTPS bootstrap acceptance missing")
cloud_log = (directory / "cloud-kanban.log").read_text(encoding="utf-8")
for required in ["RAMPI_RUST_CLOUD_KANBAN_TLS_KEYRING_OK", "RAMPI_RUST_CLOUD_KANBAN_PAGE_OK"]:
    if required not in cloud_log:
        raise SystemExit("Missing actual native cloud Kanban/keyring acceptance: " + required)
visual = json.loads((directory / "visual-acceptance.json").read_text(encoding="utf-8"))
for phase in ["startup", "hover", "focus"]:
    counts = visual.get(phase, {})
    if set(counts) != {"top", "bottom", "left", "right"} or not all(
        isinstance(value, int) and value >= 4 for value in counts.values()
    ):
        raise SystemExit("Missing actual four-edge contour evidence: " + phase)
geometry = json.loads((directory / "interaction-geometry.json").read_text(encoding="utf-8"))
captures = ["startup-" + suffix for suffix in "abcdef"] + [
    "hover-a",
    "hover-b",
    "focus-a",
    "focus-b",
    "focus-c",
    "focus-d",
    "reduced-a",
    "reduced-b",
    "settings-host",
    "settings-categories",
    "dashboard-1600",
]
for capture in captures:
    record = geometry[capture]
    expected = (1600, 900) if capture == "dashboard-1600" else (1280, 720)
    with (directory / f"interaction-{capture}.png").open("rb") as generated:
        header = generated.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) != 24:
        raise SystemExit("Missing actual interaction screenshot: " + capture)
    if (
        struct.unpack(">II", header[16:24]) != expected
        or (record["width"], record["height"]) != expected
    ):
        raise SystemExit("Unexpected interaction screenshot dimensions: " + capture)
account_log = (directory / "account-pam.log").read_text(encoding="utf-8")
if (
    "RAMPI_RUST_ACCOUNT_PAM_OK" not in account_log
    or "RAMPI_RUST_ACCOUNT_PAGE_OK" not in account_log
    or "RAMPI_RUST_ACCOUNT_CREATE_DENIED_OK" not in account_log
    or "RAMPI_RUST_ACCOUNT_CREATE_ALLOWED_OK" not in account_log
):
    raise SystemExit("Actual native account page and PAM check did not pass")
browser_log = (directory / "browser-https.log").read_text(encoding="utf-8")
for required in [
    "RAMPI_RUST_BROWSER_HTTPS_DOWNLOADS_OK",
    "RAMPI_RUST_BROWSER_UPLOAD_CONSENT_OK",
    "RAMPI_RUST_BROWSER_MODERN_INPUT_FULLSCREEN_OK",
    "RAMPI_RUST_BROWSER_PROFILE_RESTART_OK",
    "RAMPI_RUST_BROWSER_OTHER_ACCOUNT_EMPTY_OK",
]:
    if required not in browser_log:
        raise SystemExit("Actual browser acceptance missing: " + required)
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
    if "RAMPI_RUST_INSTALLER_LIFECYCLE_OK" not in (directory / "installer-lifecycle.log").read_text(
        encoding="utf-8"
    ):
        raise SystemExit("Actual ARM64 installer lifecycle did not pass")
with (directory / "rust-wayland-dashboard.png").open("rb") as image:
    header = image.read(24)
if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) != 24:
    raise SystemExit("Actual native screenshot is missing or invalid")
width, height = struct.unpack(">II", header[16:24])
if width < 960 or height < 540:
    raise SystemExit("Actual native screenshot is smaller than the supported interface")
proof = {
    "rdp_input": rdp_input,
    "required_stages": markers,
    "peak_mib": round(peak / 1024**2, 1),
    "screenshot": [width, height],
    "performance": performance,
}
(directory / "native-acceptance.json").write_text(json.dumps(proof, indent=2) + "\n")
print("PASS: every required native stage has executable evidence.")
