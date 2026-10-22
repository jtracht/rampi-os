#!/bin/bash
set -euo pipefail
install -d -m 755 "$ROOTFS_DIR/opt/rampi-build"
cp -a files/source/. "$ROOTFS_DIR/opt/rampi-build/"
# Exercise the real native installer using an ordinary-user source checkout.
chown -hR 1000:1000 "$ROOTFS_DIR/opt/rampi-build"
on_chroot <<'EOF'
DEBIAN_FRONTEND=noninteractive bash /opt/rampi-build/setup.sh --image
install -m 644 /opt/rampi-build/native/bin/source-revision.txt /opt/rampi/source-revision.txt
install -m 644 /opt/rampi-build/native/bin/binary-sha256.txt /opt/rampi/binary-sha256.txt
bash /opt/rampi-build/image/verify-rootfs.sh /
dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' > /opt/rampi/package-manifest.tsv
bash /opt/rampi-build/image/collect-licenses.sh
EOF
# Only the known, image-internal source staging tree is removed.
rm -rf -- "$ROOTFS_DIR/opt/rampi-build"
