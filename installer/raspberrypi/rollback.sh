#!/bin/bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo 'Mit sudo ausführen.' >&2; exit 1; fi
exec 9>/run/lock/rampi-install.lock
flock -x 9
previous="$(readlink -f /opt/rampi/previous)"
current="$(readlink -f /opt/rampi/current)"
for path in "$previous" "$current"; do
    if [[ "$path" != /opt/rampi/* || ! -x "$path/rampi-native" || ! -d "$path/assets" ]]; then
        echo 'Keine vollständige native Version für den Wechsel vorhanden.' >&2; exit 1
    fi
    if find "$path" \( -perm /022 -o ! -uid 0 -o ! -gid 0 \) -print -quit | grep -q .; then
        echo 'Unsichere Dateirechte im Versionsstand.' >&2; exit 1
    fi
    (cd "$path"; sha256sum --check --status SHA256SUMS)
done
"$previous/rampi-native" --version
staging="$(mktemp -d /opt/rampi/.rollback.XXXXXX)"
trap 'rm -rf -- "$staging"' EXIT
ln -s "$current" "$staging/previous"
ln -s "$previous" "$staging/current"
mv -Tf "$staging/previous" /opt/rampi/previous
mv -Tf "$staging/current" /opt/rampi/current
echo 'Vorherige Version für den nächsten Sitzungsstart ausgewählt. Persönliche Daten bleiben erhalten.'
