#!/bin/bash
set -euo pipefail
if (( EUID != 0 )); then echo "Locale installation requires root." >&2; exit 1; fi
# Add only the supported missing locale data; preserve system defaults and other locales.
for locale_name in de_DE en_US; do
    if ! locale -a | grep -Eqi "^${locale_name}[.]utf-?8$"; then
        localedef -i "$locale_name" -f UTF-8 "$locale_name.UTF-8"
    fi
done
