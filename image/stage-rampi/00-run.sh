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
python3 /opt/rampi-build/scripts/collect-debian-sources.py \
    --manifest /opt/rampi/dependency-licenses/packages-and-sources.tsv \
    --output /opt/rampi-corresponding-sources --enable-sources
EOF
# Corresponding sources are release downloads, not runtime image payload.
install -d "$DEPLOY_DIR"
tar -cJf "$DEPLOY_DIR/dependency-sources.tar.xz" -C "$ROOTFS_DIR" opt/rampi-corresponding-sources
chmod 644 "$DEPLOY_DIR/dependency-sources.tar.xz"
install -m 644 "$ROOTFS_DIR/opt/rampi-corresponding-sources/source-archives.json" "$DEPLOY_DIR/debian-source-archives.json"
rm -rf -- "$ROOTFS_DIR/opt/rampi-corresponding-sources"
# Only the known, image-internal source staging tree is removed.
rm -rf -- "$ROOTFS_DIR/opt/rampi-build"
