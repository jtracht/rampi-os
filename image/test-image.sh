#!/bin/bash
set -euo pipefail
image="$(realpath "${1:?Image path required}")"
output="$(realpath "${2:?Output directory required}")"
mkdir -p "$output"
work="$(mktemp -d)"
loop=''
cleanup() {
    if mountpoint -q "$work/boot"; then sudo umount "$work/boot"; fi
    if mountpoint -q "$work/root"; then sudo umount "$work/root"; fi
    if [[ "$loop" =~ ^/dev/loop[0-9]+$ ]]; then sudo losetup -d "$loop"; fi
    rm -rf -- "$work"
}
trap cleanup EXIT
xz -dkc "$image" > "$work/disk.img"
sfdisk --json "$work/disk.img" > "$output/partitions.json"
loop="$(sudo losetup --read-only --partscan --find --show "$work/disk.img")"
[[ "$loop" =~ ^/dev/loop[0-9]+$ ]]
sudo udevadm settle
sudo fsck.vfat -n "${loop}p1"
sudo e2fsck -fn "${loop}p2"
mkdir "$work/boot" "$work/root"
sudo mount -o ro "${loop}p1" "$work/boot"
sudo mount -o ro "${loop}p2" "$work/root"
test -f "$work/boot/kernel8.img"
test -f "$work/boot/bcm2710-rpi-3-b.dtb"
test -f "$work/root/opt/rampi/package-manifest.tsv"
test -L "$work/root/etc/systemd/system/multi-user.target.wants/rampi-health.service"
test -f "$work/root/etc/systemd/system/rampi-health.service"
sudo cp "$work/root/opt/rampi/package-manifest.tsv" "$output/package-manifest.tsv"
sudo cp "$work/root/opt/rampi/dependency-licenses.tar.xz" "$output/dependency-licenses.tar.xz"
cp "$work/boot/kernel8.img" "$work/kernel8.img"
cp "$work/boot/bcm2710-rpi-3-b.dtb" "$work/pi3.dtb"
file "$work/kernel8.img"
fdtget "$work/pi3.dtb" /aliases serial0
fdtget "$work/pi3.dtb" /aliases serial1
initrd_args=()
if [[ -f "$work/boot/initramfs8" ]]; then
    cp "$work/boot/initramfs8" "$work/initramfs8"
    initrd_args=(-initrd "$work/initramfs8")
fi
sudo umount "$work/boot" "$work/root"
sudo losetup -d "$loop"
loop=''
# The QEMU raspi3b machine requires a power-of-two SD size; pad only this temporary copy.
size="$(stat -c %s "$work/disk.img")"
power=1
while ((power < size)); do power=$((power * 2)); done
truncate -s "$power" "$work/disk.img"
set +e
timeout 300 qemu-system-aarch64 -M raspi3b -m 1G -smp 4 -nographic -monitor none \
    -no-reboot -kernel "$work/kernel8.img" -dtb "$work/pi3.dtb" \
    "${initrd_args[@]}" \
    -drive "file=$work/disk.img,format=raw,if=sd,snapshot=on" \
    -append 'root=/dev/mmcblk0p2 rootwait earlycon=pl011,mmio32,0x3f201000 console=ttyAMA1,115200 loglevel=7 systemd.unit=multi-user.target' \
    > "$output/qemu-boot.log" 2>&1 &
qemu_pid=$!
set -e
success=0
for ((attempt=0; attempt<150; attempt++)); do
    if grep -q RAMPI_BOOT_OK "$output/qemu-boot.log"; then success=1; break; fi
    if ! kill -0 "$qemu_pid" 2>/dev/null; then break; fi
    sleep 2
done
kill "$qemu_pid" 2>/dev/null || true
wait "$qemu_pid" 2>/dev/null || true
if ((success != 1)); then tail -60 "$output/qemu-boot.log"; exit 1; fi
echo 'PASS: partition/filesystem checks and QEMU Pi-3 software boot reached RAMPI_BOOT_OK.'
echo 'QEMU does not validate Wi-Fi, Bluetooth radio, HDMI, GPU decoding or real-device timing.'
