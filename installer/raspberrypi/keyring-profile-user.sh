#!/bin/sh
# Run as the profile owner; never elevate writes through personal home paths.
set -eu
mode=$1 template=$2 profile_home=$3
case "$mode" in --install|--remove) ;; *) exit 2 ;; esac
case "$profile_home" in /*) ;; *) exit 2 ;; esac
[ "$profile_home" != / ] && [ ! -L "$profile_home" ] || exit 0
[ -O "$profile_home" ] && [ -w "$profile_home" ] || exit 0
unit="$profile_home/.config/systemd/user/gnome-keyring-daemon.service"
directory="$unit.d"
target="$directory/50-rampi-pam-ordering.conf"
for path in "$profile_home/.config" "$profile_home/.config/systemd" "$profile_home/.config/systemd/user" "$directory"; do
    [ ! -L "$path" ] || exit 0
    if [ -e "$path" ] && { [ ! -d "$path" ] || [ ! -w "$path" ]; }; then exit 0; fi
done
[ ! -L "$target" ] || exit 0
if [ "$mode" = --remove ]; then
    if [ -f "$target" ] && cmp -s "$template" "$target"; then rm -- "$target"; fi
    exit 0
fi
if [ -e "$target" ]; then exit 0; fi
if [ -e "$unit" ] || [ -L "$unit" ]; then exit 0; fi
if [ -d "$directory" ] && [ -n "$(find "$directory" -mindepth 1 -maxdepth 1 -print -quit)" ]; then exit 0; fi
keyrings="$profile_home/.local/share/keyrings"
if [ -L "$keyrings" ]; then exit 0; fi
if [ -d "$keyrings" ] && [ -n "$(find "$keyrings" -name '*.keyring' -print -quit)" ]; then exit 0; fi
umask 077
mkdir -p "$directory"
install -m 644 "$template" "$target"
