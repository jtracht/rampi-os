#!/bin/bash
# Debian's ARM64 generic kernel omits this existing Linux test driver. Build
# the unmodified Debian source against the exact running kernel's own headers.
set -euo pipefail
if [[ ! -f /etc/rampi-acceptance-vm ]] || ! systemd-detect-virt --vm --quiet || [[ $EUID != 0 ]]; then
    echo 'Only the designated disposable QEMU guest may build its test driver.' >&2; exit 1
fi
if [[ "$(uname -m)" != aarch64 ]]; then
    echo 'Unexpected missing VHCI module on this architecture.' >&2; exit 1
fi
kernel="$(uname -r)"
apt-get install -y --no-install-recommends "linux-headers-$kernel" build-essential xz-utils
version="$(dpkg-query -W -f='${Version}' "linux-headers-$kernel")"
apt-get install -y --no-install-recommends "linux-source-6.12=$version"
work="$(mktemp -d /var/tmp/rampi-vhci.XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
tar --extract --xz --file /usr/src/linux-source-6.12.tar.xz --directory "$work" \
    --strip-components=3 linux-source-6.12/drivers/bluetooth/hci_vhci.c
grep -q 'SPDX-License-Identifier: GPL-2.0-or-later' "$work/hci_vhci.c"
echo "RAMPI_VHCI_DEBIAN_SOURCE=$version KERNEL=$kernel"
sha256sum "$work/hci_vhci.c"
printf 'obj-m += hci_vhci.o\n' > "$work/Makefile"
make -C "/lib/modules/$kernel/build" M="$work" -j1 modules
modprobe bluetooth
insmod "$work/hci_vhci.ko"
udevadm settle --timeout=10
test -c /dev/vhci
echo RAMPI_VHCI_DEBIAN_SOURCE_MODULE_OK
