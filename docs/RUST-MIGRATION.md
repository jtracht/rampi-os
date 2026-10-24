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
besitzt die Suchsitzung und wird beim Seitenwechsel geschlossen. Auch eine
verspätete Antwort kann dadurch keine Suche im Hintergrund zurücklassen.
`tests/rust/test-bluetooth.py` prüft die echten Rust-/GIO-Aufrufe gegen die
isolierte BlueZ-Fixture: Adapterprüfung, Suche, Lebensdauer der Verbindung,
Koppeln, Verbinden, Trennen, explizites Vertrauen und Entfernen. Mit `--ui`
betätigt der Test die tatsächliche GTK-Suchschaltfläche und prüft die Freigabe
beim Wechsel zur WLAN-Seite sowie genau ein App-Fenster. Dies belegt weder
Funkkopplung noch die Agent1-PIN-/Passkey-Seiten. Diese werden separat durch
`tests/rust/test-pairing.py` auf demselben privaten Testdienst geprüft: bewusster
Codevergleich, tatsächliche PIN-/Passkey-Antworten, Abbruch mit gelöschter Eingabe
und Abweisung eines fremden D-Bus-Absenders mit `AccessDenied`.

Der fortsetzbare [Einrichtungsassistent](NATIVE-USER-GUIDE.de.md) verwendet die
vorhandenen Einstellungsseiten. Die Hostverwaltung unterstützt mehrere persönliche
Profile, Aktivierung, Validierung und bestätigtes Entfernen. Der lokale GTK-Test
prüft diese Abläufe einschließlich gespeicherter Einrichtungsposition und
Abschluss sowie der Diagnose, ohne ein zweites Fenster zu öffnen.

Das lokale JSON-Kanban lädt beim Öffnen und per eingebauter Schaltfläche im
Hintergrund. Suche, Projekt, Priorität und Status werden kombiniert. Die
Spaltenreihenfolge wird in den persönlichen Einstellungen gespeichert;
zusätzliche Status bleiben sichtbar. Pro Spalte werden zunächst höchstens
100 Karten aufgebaut und weitere auf Wunsch eingeblendet. Quellfehler behalten
bereits geladene Aufgaben im Speicher. Der GTK-Test prüft die Filter, veränderte
Quelldaten, Fehlererhalt und dass die Anwendung keine Aufgaben zurückschreibt.
GitHub, Gitea, Trello, Jira, Asana und Notion verwenden nun native lesende Adapter,
System-Schlüsselbund und privaten persistenten Cache. [Einrichtung und Grenzen](KANBAN-NATIVE.de.md).

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
Aspekte. Tailscale zeigt seinen Zustand nun direkt in den Einstellungen anhand
von `tailscale status --json --peers=false`. Die Abfrage läuft asynchron, wird
auf 256 KiB und fünf Sekunden begrenzt und wertet keine Anmelde-URLs aus. Für
„Verbunden“ sind der Zustand `Running`, eine positive Online-Angabe und mindestens
eine gültige VPN-Adresse erforderlich. Unbekannte oder unvollständige Zustände
werden entsprechend angezeigt. Die vorhandenen Verbinden-/Trennen-/Diagnose-
Schaltflächen verwenden weiterhin die offizielle Software in einer eingebetteten
Terminalseite; die vollständige grafische Einrichtung ist offen.
Die [Tailscale-Statusabnahme](validation/rust-tailscale-2026-10-23.md) unterscheidet
echte CLI-/Dienstprüfungen von gezielten Ausgabe-/Timeout-Fixtures.

Das ist keine vollständige Funktionsabnahme. Die bisherigen Python-/QML-,
Windows-, Netzwerk- und Image-Nachweise gelten nicht automatisch für den Port.
Noch offen sind insbesondere weitere Pairing-/WLAN-Sonderfälle,
Setup-/Konten-/Tailscale-Funktionsgleichheit, persönliche Anbieteranmeldungen,
eingebettetes Streaming, Windows-NLA sowie weitere RDP-Maus-/Clipboard-Abnahmen,
weitere Installer-/Loginfälle und die vollständige Freigabe eines nativen Releases.
Die [integrierte RDP-Fläche](validation/embedded-rdp-2026-10-23.md) und die
[grafische PAM-Anmeldung](validation/graphical-login-2026-10-23.md) besitzen
inzwischen eigene native Software-Nachweise.
Die persönlichen offiziellen Anbieteranmeldungen bleiben separat zu prüfen.

`packaging/readiness.json` hält reguläre Releases während der Umstellung zurück.
Ein tatsächliches natives Entwicklungsimage ist inzwischen
[gebaut und zweimal in QEMU geprüft](validation/rust-image-2026-10-23.md),
einschließlich Programm-/Quellzuordnung und verifiziertem lokalem Download.
Die zusätzliche [grafische Image-Abnahme](validation/image-graphical-2026-10-24.md)
prüft nun auch das unverändert installierte Programm mit zwei PAM-Benutzersitzungen.
Die [ARM64-Installer-Abnahme](validation/rust-native-2026-10-23.md) prüft reale
Pakete, wiederholte Installation, Versionswechsel, Rückwechsel, abgewiesene
Fehlereingaben, erhaltene persönliche Daten und einen fremden Login-Dienst.
Die zusätzliche grafische PAM-Anmeldung ist separat geprüft; weitere
Release-Anforderungen bleiben offen.
Das zuvor veröffentlichte v0.5.0 bleibt ein Python-/QML-Release.

Die lokale Leistungsbaseline umfasst 600 überprüfte Seitenwechsel über mehr als
drei Minuten mit drei echten VTE-PTYs und lokalem WebKit-Inhalt. Gemessen werden
beobachtete Zeichenausgabe nach dem Start, Seitenwechsel, Prozess-CPU und
residenter Speicher nach der Aufwärmphase. Die JSON-Messwerte und vollständigen
Laufzeitmarker sind Pflicht für die native CI-Abnahme. Diese Pixman-/Cairo-Werte
sind kein Nachweis für physische Pi-Geschwindigkeit, GPU oder echte Remote-Last.

Zusätzlich ist der [zehnminütige Mischbetrieb](validation/mixed-soak-2026-10-24.md)
mit aktiver TLS-RDP-Verbindung, drei PTYs und WebKit auf AMD64 und ARM64 geprüft:
je 1.050 Seitenwechsel, 150 unterschiedliche Remote-Aufnahmen und vom Server
bestätigte Eingaben unter 1 GiB ohne Swap. Diese gesonderte Abnahme enthält
tatsächliche Remote-Last; sie bescheinigt weiterhin keine Pi-GPU- oder
Windows-Streaming-Leistung.

Der [native Betriebsleitfaden](NATIVE-OPERATIONS.de.md) beschreibt die vorbereiteten
Versionsordner mit zusammengehörigen Grafiken, atomare Aktivierung, manuelle
Reparatur, geprüften Rückwechsel und Deinstallation. Die ARM64-Installer-Abnahme
läuft getrennt von der Benutzeroberfläche in einem eigenen Container.

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

Die ursprüngliche eingebettete Testszene prüft lokale DOM-/JavaScript-Funktionen.
Eine zusätzliche Stufe prüft jetzt einen echten vertrauenswürdigen HTTPS-Server,
Zertifikatsfehler und Downloads. Keine dieser Stufen belegt GPU-Leistung oder
physische HDMI-/WLAN-/Bluetooth-Funktion. Physische Hardwaretests bleiben gemäß Nutzerentscheidung ausgeschlossen.

## Erweiterter nativer Stand vom 23.10.2026

OpenSSH-Schlüsselerstellung und Hostvertrauen, Live-Dashboard, versteckte WLANs,
persönliche Tastatur-/Monitor-Einstellungen, passwd/PAM-Kontoaktionen, integrierte
WebKit-Downloads und erneute Agentregistrierung nach BlueZ-Prozesswechsel sind
implementiert. Tatsächliche Wayland-Eingabe prüft Formular und Tab-Navigation,
Escape im VTE und das Compositor-Kürzel ohne Weitergabe in die PTY. Compositor-PNGs
prüfen Start/Hover/Fokus an vier unabhängigen Kanten und stillstehende reduzierte
Bewegung. Der Startimpuls wird beim Sichtbarwerden begonnen; frühere Bildstände
sind keine Nachweise dieser Korrektur. Der lokale Gesamtlauf besteht alle 20
verpflichtenden Laufzeitmarker, PAM-/HTTPS-Prüfungen, Dienstverträge, echte
WireGuard-Gegenstellen und die offizielle Tailscale-Statusprüfung unter 1 GiB.

[Reproduzierbare Entwicklung](NATIVE-DEVELOPMENT.de.md),
[Funktionsmatrix und Fehlerhilfe](NATIVE-SUPPORT.de.md), [Architektur](ARCHITECTURE.md).
