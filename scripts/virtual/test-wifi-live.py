"""Real WPA2/hostapd/supplicant/DHCP acceptance on virtual hwsim radios."""

import os
import subprocess
import time
from pathlib import Path

from rampi import wifi

if not Path("/etc/rampi-acceptance-vm").is_file() or os.getuid() == 0:
    raise SystemExit("Run as the designated ordinary user inside the QEMU acceptance VM")

secret = Path("/run/rampi-acceptance-user/wifi-key").read_text().strip()
ssid = "RampiVirtualPrivate"
manager = wifi.NetworkManager()


def network():
    for _ in range(20):
        state = wifi.snapshot(True, manager=manager)
        for row in state["networks"]:
            if row["ssid"] == ssid:
                return row
        time.sleep(1)
    raise RuntimeError("Virtual hostapd access point not discovered through NetworkManager")


def forget_own_test_profile():
    for path in manager.call(wifi.ROOT + "/Settings", wifi.NM + ".Settings", "ListConnections")[0]:
        data = manager.settings(path)
        if bytes(data.get("802-11-wireless", {}).get("ssid", [])) == ssid.encode() and data[
            "connection"
        ].get("permissions") == ["user:rampi:"]:
            manager.call(path, wifi.NM + ".Settings.Connection", "Delete")


row = network()
wifi.connect(row["key"], secret, manager=manager)
row = network()
if not row["active"] or not row["saved"]:
    raise RuntimeError("Actual WPA2 authentication did not activate the personal WLAN")
data = manager.properties(row["device"], wifi.NM + ".Device")
addresses = manager.properties(data["Ip4Config"], wifi.NM + ".IP4Config")["AddressData"]
if not any(a["address"].startswith("198.18.55.") for a in addresses):
    raise RuntimeError("Actual DHCP did not assign the expected virtual WLAN lease")
subprocess.run(
    ["ping", "-I", "wlan0", "-c", "2", "-W", "3", "198.18.55.1"],
    check=True,
    capture_output=True,
    timeout=15,
)
wifi.disconnect(row["key"], manager=manager)
time.sleep(1)
forget_own_test_profile()
try:
    wifi.connect(network()["key"], secret + "wrong", manager=manager)
except RuntimeError:
    pass
else:
    raise RuntimeError("Actual WPA2 accepted an incorrect credential")
time.sleep(1)
if network()["active"]:
    raise RuntimeError("WLAN remained connected after failed authentication")
forget_own_test_profile()
wifi.connect(network()["key"], secret, manager=manager)
if not network()["active"]:
    raise RuntimeError("Correct WPA2 credential could not reconnect after rejection")
print(
    "RAMPI_WIFI_LIVE_OK: real NM, WPA2 hostapd/supplicant authentication, DHCP, "
    "IP roundtrip, wrong credential rejection and reconnect on virtual hwsim radios",
    flush=True,
)
