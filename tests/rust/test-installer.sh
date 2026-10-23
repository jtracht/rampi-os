#!/bin/bash
# Actual install/repair/rollback lifecycle, only in a disposable native ARM64 container.
set -euo pipefail
if [[ "${RAMPI_TEST_CONTAINER:-}" != 1 || ! -f /.dockerenv || $EUID != 0 ]]; then exit 2; fi
test "$(dpkg --print-architecture)" = arm64
test ! -e /opt/rampi/current
test ! -e /opt/rampi/previous
workspace="$(mktemp -d /tmp/rampi-installer.XXXXXX)"
trap 'rm -rf -- "$workspace"' EXIT
mkdir -p "$workspace/native/bin" "$workspace/client/rampi" /home/rampi/.config/rampi
for name in installer system docs LICENSE NOTICE setup.sh; do cp -a "/src/$name" "$workspace/"; done
for name in branding icons sounds; do cp -a "/src/client/rampi/$name" "$workspace/client/rampi/"; done
install -m 755 /build/target/debug/rampi-native "$workspace/native/bin/rampi-native"
printf '%s\n' '{"setup_complete":true,"language":"de"}' > /home/rampi/.config/rampi/settings.json
personal_before="$(sha256sum /home/rampi/.config/rampi/settings.json)"
chown -hR 1000:1000 "$workspace"
# The initial installer must work before optional binutils is present.
mkdir "$workspace/prerequisites"
printf '#!/bin/sh\nexit 127\n' > "$workspace/prerequisites/readelf"
chmod 755 "$workspace/prerequisites/readelf"
PATH="$workspace/prerequisites:$PATH" bash "$workspace/setup.sh" --image
first="$(readlink -f /opt/rampi/current)"
test -x "$first/rampi-native"
test -r "$first/assets/branding/logo.png"
test -e /usr/share/wayland-sessions/rampi.desktop
test ! -e /usr/share/xsessions/rampi.desktop
test -r /etc/greetd/config.toml
if find "$first" \( -perm /022 -o ! -uid 0 -o ! -gid 0 \) -print -quit | grep -q .; then exit 1; fi
/usr/local/bin/rampi --version
if ldd "$first/rampi-native" | grep -q 'not found'; then exit 1; fi
# A second install of identical content must repair without modifying the live inode.
old_inode="$(stat -c %i "$first/rampi-native")"
bash "$workspace/setup.sh" --image
second="$(readlink -f /opt/rampi/current)"
test "$first" != "$second"
test "$(stat -c %i "$first/rampi-native")" = "$old_inode"
test "$(readlink -f /opt/rampi/previous)" = "$first"
bash "$workspace/installer/raspberrypi/rollback.sh"
test "$(readlink -f /opt/rampi/current)" = "$first"
test "$(readlink -f /opt/rampi/previous)" = "$second"
# Invalid input must not replace the selected version or run package installation.
printf 'invalid ELF\n' > "$workspace/native/bin/rampi-native"
chmod 755 "$workspace/native/bin/rampi-native"
if bash "$workspace/setup.sh" --image; then echo 'Invalid binary accepted.' >&2; exit 1; fi
test "$(readlink -f /opt/rampi/current)" = "$first"
# A changed previous version cannot be activated by rollback.
printf '\0' >> "$second/rampi-native"
if bash "$workspace/installer/raspberrypi/rollback.sh"; then echo 'Modified rollback accepted.' >&2; exit 1; fi
test "$(readlink -f /opt/rampi/current)" = "$first"
bash "$workspace/installer/raspberrypi/uninstall.sh"
test ! -e /usr/local/bin/rampi
test ! -e /usr/local/bin/rampi-wayland-start
test ! -e /usr/share/wayland-sessions/rampi.desktop
test -x "$first/rampi-native"
test -e /etc/greetd/config.toml
test "$(readlink -f /etc/systemd/system/default.target)" = /usr/lib/systemd/system/multi-user.target
test "$(sha256sum /home/rampi/.config/rampi/settings.json)" = "$personal_before"
# A subsequently selected foreign display manager must keep its graphical boot.
install -m 755 /build/target/debug/rampi-native "$workspace/native/bin/rampi-native"
bash "$workspace/setup.sh" --image
ln -sfn /usr/lib/systemd/system/foreign-test.service /etc/systemd/system/display-manager.service
bash "$workspace/installer/raspberrypi/uninstall.sh"
test "$(readlink /etc/systemd/system/display-manager.service)" = /usr/lib/systemd/system/foreign-test.service
test "$(readlink -f /etc/systemd/system/default.target)" = /usr/lib/systemd/system/graphical.target
echo RAMPI_RUST_INSTALLER_LIFECYCLE_OK
echo 'ARM64 container: real packages, repeat install, atomic version activation, rollback, rejected input and non-destructive uninstall. No PAM login or physical boot proof.'
