#!/bin/bash
# Actual installed Pi image, disposable copy, software input; no physical devices.
set -euo pipefail
image="$(realpath "${1:?Image path required}")"
output="$(realpath -m "${2:?Output directory required}")"
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -m)" == aarch64 ]]
mkdir -p "$output/captures"
expected="$(awk -v wanted="$(basename "$image")" '{name=$2;sub(/^.*\//,"",name);if(name==wanted)print $1}' "$(dirname "$image")/SHA256SUMS")"
[[ "$expected" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$expected" "$image" | sha256sum --check --status
work="$(mktemp -d)"
loop=''
qemu_pid=''
cleanup() {
    if [[ "$qemu_pid" =~ ^[0-9]+$ ]] && kill -0 "$qemu_pid" 2>/dev/null; then
        kill "$qemu_pid" 2>/dev/null || true
        wait "$qemu_pid" 2>/dev/null || true
    fi
    for point in dev proc root boot; do
        directory="$work/$point"
        [[ "$point" == dev || "$point" == proc ]] && directory="$work/root/$point"
        if mountpoint -q "$directory"; then sudo umount "$directory"; fi
    done
    if [[ "$loop" =~ ^/dev/loop[0-9]+$ ]]; then sudo losetup -d "$loop"; fi
    rm -rf -- "$work"
}
trap cleanup EXIT
xz -dc "$image" > "$work/disk.img"
loop="$(sudo losetup --partscan --find --show "$work/disk.img")"
[[ "$loop" =~ ^/dev/loop[0-9]+$ ]]
sudo udevadm settle
mkdir "$work/root" "$work/boot"
sudo mount "${loop}p2" "$work/root"
sudo mount -o ro "${loop}p1" "$work/boot"
cp "$work/boot/kernel8.img" "$work/kernel8.img"
cp "$work/boot/bcm2710-rpi-3-b.dtb" "$work/pi3.dtb"
initrd=()
if [[ -f "$work/boot/initramfs8" ]]; then
    cp "$work/boot/initramfs8" "$work/initramfs8"
    initrd=(-initrd "$work/initramfs8")
fi
fdtput -t s "$work/pi3.dtb" /soc/watchdog@7e100000 status disabled
revision="$(sudo cat "$work/root/opt/rampi/source-revision.txt")"
binary_sha="$(sudo cat "$work/root/opt/rampi/binary-sha256.txt")"
[[ "$revision" =~ ^[a-f0-9]{40}$ && "$binary_sha" =~ ^[a-f0-9]{64}$ ]]
if [[ -n "${IMAGE_PRODUCER_SHA:-}" && "$revision" != "$IMAGE_PRODUCER_SHA" ]]; then exit 1; fi
# Absolute product symlinks must resolve inside the chroot, not against the host.
sudo chroot "$work/root" /bin/sh -ec 'ldd /opt/rampi/current/rampi-native; /usr/local/bin/rampi-health' | tee "$output/installed-health.log"
grep -q RAMPI_BOOT_OK "$output/installed-health.log"
if grep -q 'not found' "$output/installed-health.log"; then exit 1; fi
printf '%s  /opt/rampi/current/rampi-native\n' "$binary_sha" | sudo chroot "$work/root" sha256sum --check --status
# Only test support is installed; no workstation package, profile or launcher is
# replaced. Deny service startup while preparing this offline disposable copy.
sudo mount --bind /dev "$work/root/dev"
sudo mount -t proc proc "$work/root/proc"
printf '#!/bin/sh\nexit 101\n' | sudo tee "$work/root/usr/sbin/policy-rc.d" > /dev/null
sudo chmod 755 "$work/root/usr/sbin/policy-rc.d"
sudo rm -f "$work/root/etc/resolv.conf"
sudo cp -L /etc/resolv.conf "$work/root/etc/resolv.conf"
sudo chroot "$work/root" dpkg-query -W | tee "$work/packages-before.tsv" > /dev/null
test_input_repo=0
if ! sudo chroot "$work/root" /bin/sh -ec 'command -v ydotool >/dev/null; command -v ydotoold >/dev/null'; then
    test ! -e "$work/root/etc/apt/sources.list.d/rampi-image-test-backports.list"
    printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie-backports main' | sudo tee "$work/root/etc/apt/sources.list.d/rampi-image-test-backports.list" > /dev/null
    test_input_repo=1
fi
sudo chroot "$work/root" /bin/sh -ec 'apt-get update -qq; DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wtype grim wlrctl python3-pil evtest; apt-get clean' 2>&1 | tee "$output/test-support-install.log"
if [[ "$test_input_repo" == 1 ]]; then
    sudo chroot "$work/root" /bin/sh -ec 'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ydotool/trixie-backports; systemctl --global disable ydotool.service; apt-get clean' 2>&1 | tee -a "$output/test-support-install.log"
    sudo rm -- "$work/root/etc/apt/sources.list.d/rampi-image-test-backports.list"
fi
sudo chroot "$work/root" dpkg-query -W | tee "$work/packages-after.tsv" > /dev/null
python3 - "$work/packages-before.tsv" "$work/packages-after.tsv" <<'PY'
import sys
from pathlib import Path
before, after = [dict(line.split("\t", 1) for line in Path(name).read_text().splitlines())
                 for name in sys.argv[1:]]
if any(after.get(name) != version for name, version in before.items()):
    raise SystemExit("Test support must not upgrade or replace installed image packages")
PY
sudo umount "$work/root/proc" "$work/root/dev"
sudo install -d -m 755 "$work/root/opt/rampi-source/scripts/virtual" "$work/root/opt/rampi-captures"
sudo install -m 644 "$source_root/scripts/virtual/test-login-guest.py" "$work/root/opt/rampi-source/scripts/virtual/"
sudo install -m 644 "$source_root/scripts/virtual/test-first-user-guest.py" "$work/root/opt/rampi-source/scripts/virtual/"
sudo install -m 644 "$source_root/scripts/check-login-evidence.py" "$work/root/opt/rampi-source/scripts/"
# Ephemeral test input, not a configured Linux account or release credential.
# The original image remains account/password-free. The existing kernel input
# tool types this only into the stock interactive wizard in the disposable copy.
python3 - "$work/first-user-credentials.json" <<'PY'
import json
import os
import secrets
import sys
with open(sys.argv[1], 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
    json.dump({"user": "abcdef", "password": ''.join(secrets.choice('abcdef') for _ in range(48))}, file)
PY
sudo install -m 600 "$work/first-user-credentials.json" "$work/root/opt/rampi-source/first-user-credentials.json"
if [[ "${RAMPI_IMAGE_GREETER_DIAGNOSTIC:-0}" == 1 ]]; then
    sudo touch "$work/root/etc/rampi-greeter-diagnostic"
fi
sudo touch "$work/root/etc/rampi-acceptance-vm" "$work/root/etc/rampi-image-acceptance-vm"
# Record the image's installed implementation before any guest test. Its config,
# executable, assets and launchers must still match after login and logout.
sudo chroot "$work/root" /bin/sh -ec 'find -L /opt/rampi/current /usr/local/lib/libmoonlight-common.so.2.7.1 /usr/local/bin/rampi /usr/local/bin/rampi-session /usr/local/bin/rampi-wayland-start /usr/local/bin/rampi-greeter /usr/local/libexec/rampi-first-user-complete /etc/systemd/system/rampi-first-user.service /etc/systemd/user/rampi.service /etc/xdg/rampi /etc/skel -type f -print0 | sort -z | xargs -0 sha256sum' | tee "$work/installed-files.sha256" > /dev/null
sudo cp "$work/installed-files.sha256" "$work/root/opt/rampi-source/installed-files.sha256"
sudo tee "$work/root/usr/local/bin/rampi-image-login-test" > /dev/null <<'SH'
#!/bin/bash
set -uo pipefail
mkdir -p /opt/rampi-captures
extra=()
if [[ -f /etc/rampi-greeter-diagnostic ]]; then extra=(--greeter-diagnostic); fi
python3 /opt/rampi-source/scripts/virtual/test-first-user-guest.py --installed-image 2>&1 | tee /opt/rampi-captures/first-user.log
result=$?
if [[ "$result" == 0 ]]; then
    python3 /opt/rampi-source/scripts/virtual/test-login-guest.py --installed-image "${extra[@]}" > /opt/rampi-captures/guest.log 2>&1
    result=$?
fi
if sha256sum --check --status /opt/rampi-source/installed-files.sha256; then
    echo RAMPI_INSTALLED_FILES_UNCHANGED_OK
else result=1
fi
if [[ -f /opt/rampi-captures/guest.log ]]; then cat /opt/rampi-captures/guest.log; fi
printf 'RAMPI_GUEST_EXIT=%s\n' "$result" > /opt/rampi-captures/result.txt
sync
cat /opt/rampi-captures/result.txt
systemctl poweroff
SH
sudo chmod 755 "$work/root/usr/local/bin/rampi-image-login-test"
sudo tee "$work/root/etc/systemd/system/rampi-image-login-test.service" > /dev/null <<'UNIT'
[Unit]
Description=Disposable QEMU installed-image graphical acceptance
After=systemd-logind.service systemd-user-sessions.service
Wants=systemd-logind.service systemd-user-sessions.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/rampi-image-login-test
TimeoutStartSec=2100
StandardOutput=journal+console
StandardError=journal+console
UNIT
sudo umount "$work/boot" "$work/root"
sudo losetup -d "$loop"
loop=''
size="$(stat -c %s "$work/disk.img")"
power=1
while ((power < size)); do power=$((power * 2)); done
truncate -s "$power" "$work/disk.img"
set +e
timeout 2400 qemu-system-aarch64 -M raspi3b -accel tcg,thread=multi -m 1G -smp 4 -nographic -monitor none -nic none \
    -no-reboot -kernel "$work/kernel8.img" -dtb "$work/pi3.dtb" "${initrd[@]}" \
    -device usb-kbd -device usb-tablet \
    -drive "file=$work/disk.img,format=raw,if=sd" \
    -append 'root=/dev/mmcblk0p2 rootfstype=ext4 rw rootwait console=ttyAMA1,115200 plymouth.enable=0 systemd.unit=multi-user.target systemd.wants=rampi-image-login-test.service rampi.image_acceptance=1' \
    > "$output/serial.log" 2>&1 &
qemu_pid=$!
guest_result=''
for ((attempt=0; attempt<1200; attempt++)); do
    guest_result="$(sed -n 's/.*RAMPI_GUEST_EXIT=\([0-9][0-9]*\).*/\1/p' "$output/serial.log" | tail -1)"
    if [[ -n "$guest_result" ]] || ! kill -0 "$qemu_pid" 2>/dev/null; then break; fi
    sleep 2
done
# The temporary DTB disables the emulated PM/watchdog peripheral. Do not depend
# on a physical poweroff operation: all guest writes were synced before its
# explicit result marker, so stop the emulator only after that result arrives.
if kill -0 "$qemu_pid" 2>/dev/null; then kill "$qemu_pid"; fi
wait "$qemu_pid"
qemu_result=$?
qemu_pid=''
set -e
loop="$(sudo losetup --partscan --find --show "$work/disk.img")"
sudo udevadm settle
# The emulator is stopped after sync, while ext4 may still be mounted in the
# guest. Replay only the disposable copy's committed journal before reading it.
set +e
sudo e2fsck -p "${loop}p2" 2>&1 | tee "$output/working-copy-fsck.log"
fsck_result=${PIPESTATUS[0]}
set -e
if ((fsck_result > 1)); then cat "$output/working-copy-fsck.log"; exit 1; fi
sudo mount -o ro "${loop}p2" "$work/root"
sudo cp -a "$work/root/opt/rampi-captures/." "$output/captures/"
sudo chown -R "$(id -u):$(id -g)" "$output/captures"
sudo umount "$work/root"
sudo losetup -d "$loop"
loop=''
python3 - "$output" "$binary_sha" "$revision" "$expected" "$qemu_result" "$guest_result" <<'PY'
import json
import sys
from pathlib import Path
directory = Path(sys.argv[1])
data = dict(architecture="arm64", memory_mib=1024, cpus=4, physical_devices=False,
            tcg_thread="multi",
            prepared_development_cache=False, resumed_development_guest=False,
            graphical_login=True, installed_pi_image=True, machine="raspi3b",
            native_binary_sha256=sys.argv[2], image_source_revision=sys.argv[3],
            original_compressed_image_sha256=sys.argv[4], qemu_observed_exit_code=int(sys.argv[5]),
            guest_exit_code=int(sys.argv[6]) if sys.argv[6] else None,
            stopped_after_synced_guest_result=bool(sys.argv[6]),
            temporary_dtb_watchdog_disabled=True,
            test_support_packages=["wtype", "grim", "wlrctl", "python3-pil", "evtest", "ydotool"])
(directory / "environment.json").write_text(json.dumps(data, indent=2) + "\n")
PY
[[ "$guest_result" == 0 ]]
python3 "$source_root/scripts/check-image-login-evidence.py" "$output" --expected-source "$revision" --expected-image-sha256 "$expected"
printf '%s  %s\n' "$expected" "$image" | sha256sum --check --status
echo 'RAMPI_INSTALLED_IMAGE_GRAPHICAL_OK: original image unchanged; actual installed GUI, PAM and two accounts tested in disposable QEMU copy.'
