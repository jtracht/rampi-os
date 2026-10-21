# Rust- und Wayland-Umstellung

Verbindliche Architekturänderung vom 21. Oktober 2026: Anwendung und Oberfläche
werden in Rust entwickelt. Die grafische Sitzung verwendet Wayland mit labwc;
`startx`, Xorg und Openbox gehören nicht zur neuen Laufzeit.

GTK 4 stellt Widgets, Eingabe, Fokus, Barrierefreiheit und Cairo bereit.
libcanberra übernimmt die kurzen UI-Klänge über den vorhandenen PulseAudio-
beziehungsweise PipeWire-Pulse-Dienst. VTE
stellt das eingebettete Terminal einschließlich PTY bereit. WebKitGTK stellt
die eingebettete Browser-Engine bereit. Diese Komponenten werden über ihre
Rust-Bindings verwendet. Rampi entwickelt keine eigenen Ersatzprotokolle,
Terminal- oder Browser-Engines und keinen eigenen Compositor.

## Quellcode und Start

- `native/core`: persönliche Konfiguration, Kanban, Verbindungsargumente,
  Bewegungsparameter; plattformunabhängig und unter Windows testbar.
- `native/ui`: vollständiger GTK-Widgetaufbau in Rust, asynchrone GIO-Aufrufe,
  WLAN-/Bluetooth-Seiten, BlueZ-Agent, eingebettetes VTE und WebKitGTK.
- `system/rampi-session`: vorhandene Wayland-Sitzung wiederverwenden oder
  labwc starten; keine zusätzliche grafische Sitzung innerhalb eines Compositors.
- `system/rampi-wayland-start`: Umgebung in systemd importieren und den
  vorhandenen systemd-Benutzerdienst starten.
- `installer/raspberrypi/setup.sh`: ARM64-Binary installieren und vorhandene
  Pakete erkennen. Ein fehlendes Binary wird nicht durch Python ersetzt.

Shell- und PowerShell-Dateien bleiben für Installation und die Integration
vorhandener Linux-/Windows-Werkzeuge erhalten. Die neue grafische Anwendung
benötigt weder Python noch QML. `client/` enthält während der Portierung den
historischen Prototyp und die weiterverwendeten Grafik-/Klangdateien.

Für die Entwicklung unter Linux mit installierten GTK-/VTE-/WebKit-Headern:

```sh
cargo test --locked -p rampi-core
RAMPI_ASSETS="$PWD/client/rampi" cargo run --locked -p rampi-ui -- --windowed
```

Die Quelle wird mit `Cargo.lock` und einem festgelegten offiziellen Rust-/Debian-
Container gebaut. Die CI kompiliert nativ für amd64 und arm64. Es wird nicht auf
dem Raspberry Pi kompiliert; Installer erwarten ein vorgebautes ARM64-Binary.

## Nachgewiesen und noch offen

Lokal auf amd64 und in der CI auf amd64 und arm64 nachgewiesen; die vollständigen
CI-Artefakte sind separat [verifiziert](validation/rust-wayland-2026-10-21.md): Rust-Core-Tests; vollständiger Linux-Build; Clippy ohne
Warnungen; echte labwc-Sitzung mit `GdkWaylandDisplay`, einem App-Fenster und
getrennten Einstellungsseiten; tatsächliche VTE-PTY-Ein-/Ausgabe; tatsächliche
WebKit-DOM-/JavaScript-Ausführung; Rust-/GIO-Aufrufe gegen eine private
NetworkManager-Fixture; tatsächliche Klick-Audioausgabe über libcanberra/PulseAudio. Die Laufzeitprüfung verwendet ein Limit von
1 GiB. Im Test laufen weder Xorg noch Xwayland noch `startx`.

Bluetooth verwendet eine Adapterliste direkt in der Seite, ohne Ausklappfenster.
Gefundene Geräte werden während der sichtbaren Seite automatisch aktualisiert;
unveränderte Listen werden nicht neu aufgebaut. Eine eigene D-Bus-Verbindung
besitzt die Suchsitzung und wird beim Tab-/Seitenwechsel geschlossen. Auch eine
verspätete Antwort kann dadurch keine Suche im Hintergrund zurücklassen.
`tests/rust/test-bluetooth.py` prüft die echten Rust-/GIO-Aufrufe gegen die
isolierte BlueZ-Fixture: Adapterprüfung, Suche, Lebensdauer der Verbindung,
Koppeln, Verbinden, Trennen, explizites Vertrauen und Entfernen. Mit `--ui`
betätigt der Test die tatsächliche GTK-Suchschaltfläche und prüft die Freigabe
beim Wechsel zum WLAN-Tab sowie genau ein App-Fenster. Dies belegt weder
Funkkopplung noch die Agent1-PIN-/Passkey-Dialoge.

Das lokale JSON-Kanban lädt beim Öffnen und per eingebauter Schaltfläche im
Hintergrund. Suche, Projekt, Priorität und Status werden kombiniert. Die
Spaltenreihenfolge wird in den persönlichen Einstellungen gespeichert;
zusätzliche Status bleiben sichtbar. Pro Spalte werden zunächst höchstens
100 Karten aufgebaut und weitere auf Wunsch eingeblendet. Quellfehler behalten
bereits geladene Aufgaben im Speicher. Der GTK-Test prüft die Filter, veränderte
Quelldaten, Fehlererhalt und dass die Anwendung keine Aufgaben zurückschreibt.
Cloud-Connectoren und ein persistenter Cloud-Offline-Cache sind noch nicht portiert.

Die VPN-Seite bietet persönliche WireGuard-Profile direkt als Liste an, ohne
externen Verbindungsmanager. Der libnm-Importer liest eine private, auf 64 KiB
begrenzte Kopie der gewählten `.conf`-Datei. Erst danach setzt Rust die persönliche
NetworkManager-Berechtigung anhand des tatsächlichen Linux-Kontos und deaktiviert
Autostart; diese Werte werden zusammen mit dem Profil gespeichert. Rampi verändert
die Quelldatei nicht und speichert keine eigene Schlüsselkopie dauerhaft.
NetworkManager übernimmt seine vorhandene Schlüsselablage und Tunnelverwaltung.
Gemeinsame, fremde und mehreren Benutzern zugewiesene Profile sind ausgeschlossen;
jede Verbindung prüft die aktuelle Zuordnung erneut. Der GUI-Test und die
[echten WireGuard-Gegenstellen](validation/rust-vpn-2026-10-21.md) prüfen getrennte
Aspekte. Die Tailscale-Schaltflächen verwenden weiterhin die offizielle Software
in einer eingebetteten Terminalseite; ihre vollständige grafische Einrichtung ist offen.

Das ist keine vollständige Funktionsabnahme. Die bisherigen Python-/QML-,
Windows-, Netzwerk- und Image-Nachweise gelten nicht automatisch für den Port.
Noch offen sind insbesondere die umfassende Rust-D-Bus-/Pairing-Abnahme,
WLAN-Sonderfälle, Setup-/Konten-/Tailscale-Funktionsgleichheit, alle Kanban-Anbieter,
Streaming, integrierte Remote-Desktop-Darstellung, grafische PAM-Anmeldung,
Installer-Reparaturpfade, das neue ARM64-Systemimage und seine QEMU-Abnahme.
Die persönlichen offiziellen Anbieteranmeldungen bleiben separat zu prüfen.

`packaging/readiness.json` hält reguläre Releases während der Umstellung zurück.
Es wird kein neues Image als fertig ausgewiesen, solange diese Prüfungen fehlen.
Das zuvor veröffentlichte v0.5.0 bleibt ein Python-/QML-Release.

## Isolierter Wayland-Test

Der Test verwendet einen virtuellen labwc-Ausgang mit Pixman, ohne Host-GPU,
Host-Eingabegeräte oder physischen Raspberry Pi. Der Container läuft als normaler
Benutzer mit deaktiviertem Netzwerk, schreibgeschütztem Quellcode und einem
eigenen Ausgabeordner. Docker muss unprivilegierte User-Namespaces zulassen:
für diesen Test werden sein Seccomp-Filter und das Docker-AppArmor-Profil
ausgesetzt. `systempaths=unconfined` hebt zusätzlich Dockers Maskierung von
Systempfaden im Container auf, damit Bubblewrap ein eigenes `/proc` in seinem
PID-Namespace einhängen kann; siehe [Docker-Laufzeitoptionen](https://docs.docker.com/reference/cli/docker/container/run).
Die WebKit-Sandbox selbst
bleibt eingeschaltet; `WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS` wird nicht gesetzt.
Diese Containeroption gehört ausschließlich zur Testumgebung.
Auf den kurzlebigen Ubuntu-24.04-GitHub-VMs wird außerdem die dortige
[AppArmor-Beschränkung für unprivilegierte User-Namespaces](https://documentation.ubuntu.com/release-notes/24.04/)
für den Laufzeittest vorübergehend aufgehoben und im selben Schritt per Trap
wiederhergestellt. Diese Einstellung wird nicht vom Rampi-Installer verändert.

Die Testszene prüft lokale DOM-/JavaScript-Funktionen. Sie belegt keine erfolgreiche
HTTPS-Verbindung, keine GPU-Leistung und keine physische HDMI-/WLAN-/Bluetooth-
Funktion. Physische Hardwaretests bleiben gemäß Nutzerentscheidung ausgeschlossen.
