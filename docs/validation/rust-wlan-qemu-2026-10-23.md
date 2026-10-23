# Native WLAN-Abnahme in QEMU, 23. Oktober 2026

Bezug: `b6719ce` auf `codex/software-acceptance-85` (historischer Branchname).
Das aktuelle Nutzerziel beträgt mindestens **75 %**, nicht mehr 85 %.
WLAN steigt von 3 auf 4 Punkte; Gesamtstand damit **72 / 100**.

Der Test startet einen vollständigen Debian-13-Gast mit 1 GiB RAM, vier virtuellen
CPUs und QEMU 10.0.13. Der Gastkernel `6.12.113+deb13-amd64` stellt zwei
`mac80211_hwsim`-Radios bereit. Ein eigener Netzwerk-Namespace betreibt hostapd
mit zufälligem WPA2-Kennwort und dnsmasq für DHCP. Es werden keine Host-Funkgeräte
oder physischen Raspberry-Pi-Geräte weitergereicht.

Das Rust-Prüfprogramm bindet unmittelbar dieselbe `bus.rs` ein wie die
produktiv genutzte GTK-Oberfläche. Es läuft als normaler Linux-Benutzer und ruft
den echten NetworkManager über GIO/D-Bus auf. Die Test-Policy gewährt diesem
Konto ausschließlich die erforderlichen Netzwerkaktionen. Das ist kein Test
der späteren Policy einer grafisch angemeldeten Raspberry-Pi-Sitzung.

Bestanden:

- Erkennen des virtuellen Access Points, WPA2-Anmeldung und privates gespeichertes Profil.
- Tatsächliche DHCP-Adresse und IP-Rundlauf zum Access Point.
- Trennen, Ablehnung eines falschen Kennworts und anschließende Wiederverbindung.
- Ein zweites Linux-Konto kann das persönliche Profil nicht übernehmen.
- Anschließend zusätzlich die vorhandene Python-Vergleichsabnahme desselben Netzes.

Serielle Erfolgsmarker: `RAMPI_RUST_WIFI_LIVE_OK`,
`RAMPI_RUST_WIFI_OTHER_USER_OK`, `RAMPI_WIFI_LIVE_OK`,
`RAMPI_VIRTUAL_ACCEPTANCE_OK`, `RAMPI_GUEST_EXIT=0`.

SHA256 der geprüften Rust-Prüfdatei:
`ce59f07620519b8a2c25b18134bcf0e1834694363e132083459ddb646344b981`.
Der offizielle Debian-Ausgangsstand ist `20261017-2634`; dessen SHA512 wird
vor jedem Start gegen die im Runner festgelegte Prüfsumme geprüft.
Der lokale Lauf verwendete den ausdrücklich gekennzeichneten vorbereiteten
OS-Cache. Die neue CI-Stufe startet vom unveränderten offiziellen Ausgangsimage.

Wiederholung in der vorgesehenen Linux-Docker-Testumgebung:

```sh
docker build -f tests/virtual/Dockerfile -t rampi-virtual-tools .
docker run --rm --memory=3g --memory-swap=3g --cpus=4 \
  -v "$PWD:/app" -v rampi-rust-build:/build:ro rampi-virtual-tools \
  python3 scripts/test-virtual-linux.py \
  --native-binary /build/target/debug/rampi-network-acceptance
```

Vorher die Rust-Binaries mit der nativen Testumgebung bauen. Protokoll und
Umgebungsdaten entstehen unter `artifacts/virtual-linux/`. Das Gastbudget ist
1 GiB; das größere Docker-Budget umfasst zusätzlich QEMU und die Werkzeuge.
WPA3, Enterprise-WLAN, physische Funkqualität und die ARM64-Gastwiederholung
sind hier nicht nachgewiesen. Hardwaretests bleiben auf Nutzerwunsch ausgeschlossen.

## Frischer CI-Gast bestätigt

Die [abschließende native CI](https://github.com/jtracht/rampi-os/actions/runs/39943739204)
bestätigt denselben Rust-WLAN-Adapter zusätzlich ohne vorbereiteten OS-Cache.
Die Umgebungsdatei weist `prepared_development_cache=false` aus; sämtliche
nativen WLAN- und Vergleichsmarker sowie `RAMPI_GUEST_EXIT=0` sind vorhanden.
Die vollständige CI ist einschließlich ARM64-Installer und nativen Paketen grün.
