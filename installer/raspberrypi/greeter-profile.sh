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

# Only the exact, recorded Rampi default is eligible. A locally changed greeter,
# profile or branding file keeps its existing login path and appearance.
rampi_migrate_greeter_branding() {
    local source_root="$1" config="$2" marker="$3" profile="$4" colors="$5" expected actual
    for path in "$config" "$marker" "$profile"; do
        [[ -f "$path" && ! -L "$path" ]] || return 0
    done
    [[ ! -L "$colors" ]] || return 0
    if [[ -e "$colors" ]]; then
        cmp -s "$colors" "$source_root/system/wlgreet.toml" || return 0
    fi
    expected="$(cat "$marker")"
    [[ "$expected" =~ ^[a-f0-9]{64}$ ]] || return 0
    actual="$(sha256sum "$config" | cut -d ' ' -f 1)"
    [[ "$actual" == "$expected" ]] || return 0
    cmp -s "$profile" "$source_root/system/labwc/greeter.xml" || return 0
    cmp -s "$config" "$source_root/system/greetd-unbranded.toml" || return 0
    install -m 644 "$source_root/system/wlgreet.toml" "$colors"
    install -m 644 "$source_root/system/greetd.toml" "$config"
    sha256sum "$config" | cut -d ' ' -f 1 > "$marker"
    echo 'Rampi-Logo für die unveränderte verwaltete Anmeldung aktiviert.'
}
