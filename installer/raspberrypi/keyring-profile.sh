#!/bin/bash
# Manage only first-login defaults for the existing GNOME daemon.
set -euo pipefail
mode="${1:---install}"
[[ $EUID == 0 ]] || { echo 'Root required for installer profile management.' >&2; exit 1; }
[[ "$mode" == --install || "$mode" == --remove ]] || exit 2
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ "$mode" == --install ]]; then
    unit=/usr/lib/systemd/user/gnome-keyring-daemon.service
    [[ -f "$unit" ]] || exit 0
    expected="$(dpkg-query --control-show gnome-keyring md5sums | \
        awk '$2 == "usr/lib/systemd/user/gnome-keyring-daemon.service" {print $1}')"
    [[ "$expected" =~ ^[a-f0-9]{32}$ ]] || exit 0
    [[ "$(md5sum "$unit" | cut -d ' ' -f 1)" == "$expected" ]] || exit 0
    grep -Eq '^ExecStart=/usr/bin/gnome-keyring-daemon --foreground --components=("pkcs11,secrets"|pkcs11,secrets) --control-directory=%t/keyring$' "$unit" || exit 0
    for directory in /etc/systemd/user /run/systemd/user /usr/local/lib/systemd/user; do
        [[ ! -e "$directory/gnome-keyring-daemon.service" && ! -L "$directory/gnome-keyring-daemon.service" ]] || exit 0
        if [[ -d "$directory/gnome-keyring-daemon.service.d" ]] && \
            [[ -n "$(find "$directory/gnome-keyring-daemon.service.d" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then exit 0; fi
    done
fi
# The caller's checkout may be inside a different user's private home. Stage
# only public installer code before dropping privileges, never credentials.
staging="$(mktemp -d /tmp/rampi-keyring-profile.XXXXXX)"
trap 'rm -rf -- "$staging"' EXIT
chmod 755 "$staging"
install -m 644 "$root/installer/raspberrypi/keyring-profile-user.sh" "$staging/apply.sh"
install -m 644 "$root/system/rampi-keyring-ordering.conf" "$staging/profile.conf"
sh "$staging/apply.sh" "$mode" "$staging/profile.conf" /etc/skel
while IFS=: read -r name _password uid _gid _description profile_home shell; do
    [[ "$uid" =~ ^[0-9]+$ && "$uid" -ge 1000 && "$uid" -lt 65534 && -d "$profile_home" ]] || continue
    [[ "$shell" != */nologin && "$shell" != */false ]] || continue
    runuser -u "$name" -- sh "$staging/apply.sh" "$mode" "$staging/profile.conf" "$profile_home"
    if [[ -S "/run/user/$uid/bus" ]]; then
        runuser -u "$name" -- env "XDG_RUNTIME_DIR=/run/user/$uid" \
            "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus" \
            systemctl --user daemon-reload 2>/dev/null || true
    fi
done < <(getent passwd)
