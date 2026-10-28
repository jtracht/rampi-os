#!/bin/bash
# Exercise actual distribution locale data in a disposable root SDK container only.
set -euo pipefail
if [[ "${RAMPI_TEST_CONTAINER:-}" != 1 || ! -f /.dockerenv || $EUID != 0 ]]; then exit 2; fi
snapshot_defaults() {
    for setting in /etc/default/locale /etc/locale.gen; do
        if [[ -f "$setting" ]]; then sha256sum "$setting"; else printf '%s missing\n' "$setting"; fi
    done
}
test "$(id -u rampi)" -ne 0
localedef -i fr_FR -f UTF-8 fr_FR.UTF-8
before="$(snapshot_defaults)"
bash installer/raspberrypi/locales.sh
archive="$(sha256sum /usr/lib/locale/locale-archive)"
bash installer/raspberrypi/locales.sh
test "$archive" = "$(sha256sum /usr/lib/locale/locale-archive)"
test "$before" = "$(snapshot_defaults)"
locale -a | grep -qi '^fr_FR[.]utf8$'
for selected in de_DE.UTF-8 en_US.UTF-8; do
    LC_MESSAGES="$selected" LC_TIME="$selected" python3 -c 'import locale; locale.setlocale(locale.LC_MESSAGES, ""); locale.setlocale(locale.LC_TIME, "")'
done
if runuser -u rampi -- bash installer/raspberrypi/locales.sh; then exit 1; fi
printf '%s\n' RAMPI_RUST_PERSONAL_LOCALES_INSTALL_OK
