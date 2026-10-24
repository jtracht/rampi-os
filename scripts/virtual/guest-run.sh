#!/bin/bash
set -euo pipefail
if [[ ! -f /etc/rampi-acceptance-vm ]] || ! systemd-detect-virt --vm --quiet; then
    echo 'This acceptance script requires its designated QEMU guest.' >&2; exit 1
fi
echo RAMPI_VIRTUAL_KERNEL="$(uname -r)"
modprobe mac80211_hwsim radios=2
if modinfo hci_vhci >/dev/null 2>&1; then
    modprobe hci_vhci
else
    bash /opt/rampi-source/scripts/virtual/ensure-vhci.sh
fi
modprobe uinput
btvirt -l2 >/tmp/rampi-btvirt.log 2>&1 &
bt_pid=$!
trap 'kill "$bt_pid" 2>/dev/null || true' EXIT
sleep 2
iw dev
bluetoothctl list
if [[ "${1:-}" == --probe ]]; then
    test "$(iw dev | awk '/Interface / {count++} END {print count}')" -eq 2
    test "$(bluetoothctl list | wc -l)" -eq 2
    echo RAMPI_VIRTUAL_PROBE_OK
    exit 0
fi
useradd --create-home --shell /bin/bash rampi
useradd --create-home --shell /bin/bash rampi-other
install -d -m 700 /run/rampi-acceptance-root
install -d -m 700 -o rampi -g rampi /run/rampi-acceptance-user
python3 - <<'PY'
import os, pwd, uuid
from pathlib import Path
secret = uuid.uuid4().hex
root = Path('/run/rampi-acceptance-root')  # pragma: allowlist secret - public fixture path
config = ('interface=wlan1\ndriver=nl80211\nssid=RampiVirtualPrivate\n'
          'hw_mode=g\nchannel=1\nwpa=2\nwpa_key_mgmt=WPA-PSK\nrsn_pairwise=CCMP\n'  # pragma: allowlist secret - public hostapd constants
          'wpa_passphrase=' + secret + '\n')
(root / 'hostapd.conf').write_text(config)
key = Path('/run/rampi-acceptance-user/wifi-key')
key.write_text(secret)
account = pwd.getpwnam('rampi')
os.chown(key, account.pw_uid, account.pw_gid)
os.chmod(key, 0o600)
PY
cat > /etc/polkit-1/rules.d/49-rampi-acceptance.rules <<'RULE'
polkit.addRule(function(action, subject) {
  if (subject.user === 'rampi' &&
      (action.id === 'org.freedesktop.NetworkManager.settings.modify.own' ||
       action.id === 'org.freedesktop.NetworkManager.network-control' ||
       action.id === 'org.freedesktop.NetworkManager.wifi.scan')) return polkit.Result.YES;
});
RULE
rfkill unblock all
nmcli radio wifi on
nmcli device set wlan1 managed no
nmcli device set wlan0 managed yes
ip netns add rampi-ap
iw phy phy1 set netns name rampi-ap
ip netns exec rampi-ap ip link set lo up
ip netns exec rampi-ap ip link set wlan1 up
ip netns exec rampi-ap ip addr add 198.18.55.1/24 dev wlan1
ip netns exec rampi-ap hostapd -B -P /run/rampi-acceptance-root/hostapd.pid /run/rampi-acceptance-root/hostapd.conf
ip netns exec rampi-ap dnsmasq --no-daemon --port=0 --interface=wlan1 --bind-interfaces \
    --dhcp-range=198.18.55.10,198.18.55.30,255.255.255.0,1h --dhcp-option=3 --dhcp-option=6 \
    >/run/rampi-acceptance-root/dnsmasq.log 2>&1 &
dns_pid=$!
trap 'kill "$bt_pid" "$dns_pid" 2>/dev/null || true' EXIT
if [[ -f /opt/rampi-source/rampi-network-acceptance ]]; then
    runuser -u rampi -- /opt/rampi-source/rampi-network-acceptance
    runuser -u rampi-other -- /opt/rampi-source/rampi-network-acceptance --other
    python3 /opt/rampi-source/scripts/virtual/test-bluetooth-live.py
fi
runuser -u rampi -- env PYTHONPATH=/opt/rampi-source/client \
    python3 /opt/rampi-source/scripts/virtual/test-wifi-live.py
if [[ -f /opt/rampi-source/rampi-network-acceptance ]]; then
    python3 /opt/rampi-source/scripts/virtual/test-wifi-modes.py
fi
echo RAMPI_VIRTUAL_ACCEPTANCE_OK
