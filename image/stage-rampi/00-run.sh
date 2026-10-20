#!/bin/bash
set -euo pipefail
install -d -m 755 "$ROOTFS_DIR/opt/rampi-build"
cp -a files/source/. "$ROOTFS_DIR/opt/rampi-build/"
# Exercise the real installer with ordinary-user source ownership, as on a
# downloaded checkout. Installed shared code must still become root-owned.
chown -hR 1000:1000 "$ROOTFS_DIR/opt/rampi-build/client/rampi"
on_chroot <<'EOF'
DEBIAN_FRONTEND=noninteractive bash /opt/rampi-build/setup.sh --image
bash /opt/rampi-build/image/verify-rootfs.sh /
dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' > /opt/rampi/package-manifest.tsv
bash /opt/rampi-build/image/collect-licenses.sh
EOF
# Only the known, image-internal source staging tree is removed.
rm -rf -- "$ROOTFS_DIR/opt/rampi-build"
