#!/bin/bash
set -euo pipefail
image="$(realpath "${1:?Image path required}")"
output="$(realpath "${2:?Output directory required}")"
mkdir -p "$output"
# Verify the exact downloaded artifact, including older producer manifests that
# recorded an absolute build path. Never use that path as a filesystem target.
manifest="$(dirname "$image")/SHA256SUMS"
expected="$(awk -v wanted="$(basename "$image")" '{name=$2; sub(/^.*\//,"",name); if(name==wanted) print $1}' "$manifest")"
[[ "$expected" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$expected" "$image" | sha256sum --check --status
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
test -f "$work/root/etc/systemd/system/rampi-health.service"
test -f "$work/boot/bcm2710-rpi-3-b-plus.dtb"
test -f "$work/root/usr/share/wayland-sessions/rampi.desktop"
test -f "$work/root/etc/xdg/rampi/labwc/rc.xml"
test -f "$work/root/usr/share/doc/rampi/rust-licenses/packages.json"
test -f "$work/root/usr/share/doc/rampi/rust-licenses/Rust-standard-library-COPYRIGHT.html"
revision="$(sudo cat "$work/root/opt/rampi/source-revision.txt")"
[[ "$revision" =~ ^[a-f0-9]{40}$ ]]
if [[ -n "${IMAGE_PRODUCER_SHA:-}" && "$revision" != "$IMAGE_PRODUCER_SHA" ]]; then
    echo 'Image-Quellrevision passt nicht zum erzeugenden Workflow.' >&2; exit 1
fi
binary_sha="$(sudo cat "$work/root/opt/rampi/binary-sha256.txt")"
[[ "$binary_sha" =~ ^[a-f0-9]{64}$ ]]
selected="$(sudo readlink "$work/root/opt/rampi/current")"
[[ "$selected" == /opt/rampi/* && "$selected" != *..* ]]
binary="$work/root$selected/rampi-native"
printf '%s  %s\n' "$binary_sha" "$binary" | sudo sha256sum --check --status
readelf -h "$binary" | grep -q AArch64
printf 'source_revision=%s\nbinary_sha256=%s\n' "$revision" "$binary_sha" > "$output/native-image-provenance.txt"
echo RAMPI_NATIVE_IMAGE_METADATA_OK
sudo cp "$work/root/opt/rampi/package-manifest.tsv" "$output/package-manifest.tsv"
sudo cp "$work/root/opt/rampi/dependency-licenses.tar.xz" "$output/dependency-licenses.tar.xz"
cp "$work/boot/kernel8.img" "$work/kernel8.img"
cp "$work/boot/bcm2710-rpi-3-b.dtb" "$work/pi3.dtb"
file "$work/kernel8.img"
fdtget "$work/pi3.dtb" /aliases serial0
fdtget "$work/pi3.dtb" /aliases serial1
# QEMU 8.2 resets immediately on a watchdog control write, even while the
# initramfs is disarming the real Pi watchdog. Disable only that emulated
# peripheral in this temporary DTB. The shipped DTB and image stay unchanged.
fdtput -t s "$work/pi3.dtb" /soc/watchdog@7e100000 status disabled
printf '%s\n' 'raspi3b; 1 GiB; 4 CPUs; original Pi kernel and initramfs.' \
    'Temporary DTB: watchdog disabled because QEMU treats its disarm write as reset.' \
    'Serial console uses ttyAMA1 according to the original DTB serial1 alias.' \
    'Boot probe explicitly requested with systemd.wants; writable runtime overlay; Plymouth off for serial diagnostics.' \
    'Original image readonly checked; runtime writes use QEMU snapshot overlay.' \
    > "$output/qemu-environment.txt"
qemu-system-aarch64 --version >> "$output/qemu-environment.txt"
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
    -append 'root=/dev/mmcblk0p2 rootfstype=ext4 rw rootwait earlycon=pl011,mmio32,0x3f201000 console=ttyAMA1,115200 loglevel=6 plymouth.enable=0 systemd.show_status=yes systemd.unit=multi-user.target systemd.wants=rampi-health.service' \
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
grep -q 'Rampi .*Rust / Wayland' "$output/qemu-boot.log"
echo 'PASS: partition/filesystem checks and QEMU Pi-3 software boot reached RAMPI_BOOT_OK.'
echo 'QEMU does not validate Wi-Fi, Bluetooth radio, HDMI, GPU decoding or real-device timing.'
