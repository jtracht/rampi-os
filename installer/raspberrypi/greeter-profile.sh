#!/bin/bash
# Upgrade only Rampi's unchanged, recorded legacy greeter profile.
rampi_migrate_greeter_profile() {
    local source_root="$1" config="$2" marker="$3" profile="$4" expected actual
    for path in "$config" "$marker" "$profile"; do
        [[ -f "$path" && ! -L "$path" ]] || return 0
    done
    expected="$(cat "$marker")"
    [[ "$expected" =~ ^[a-f0-9]{64}$ ]] || return 0
    actual="$(sha256sum "$config" | cut -d ' ' -f 1)"
    [[ "$actual" == "$expected" ]] || return 0
    cmp -s "$profile" "$source_root/system/labwc/rc.xml" || return 0
    install -m 644 "$source_root/system/labwc/greeter.xml" "$profile"
    echo 'Unverändertes Rampi-Anmeldeprofil aktualisiert; eigene Login-Konfigurationen bleiben erhalten.'
}
