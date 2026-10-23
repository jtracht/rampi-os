# Rust-/Wayland-Nachweis vom 21. Oktober 2026

Entwicklungszweig: `codex/software-acceptance-85`.
Die Umstellung ist noch kein regulärer Release.

Geprüfte Code-Revision: `187894bae8f05b8ec9ddd73497bc643b1ccf6fbb`.
Die [Rust-/Wayland-CI](https://github.com/jtracht/rampi-os/actions/runs/39546481258)
ist für amd64 und arm64 erfolgreich. Die [bestehende CI](https://github.com/jtracht/rampi-os/actions/runs/39546481296)
ist mit allen sechs Jobs ebenfalls erfolgreich. Die Artefakte
`rust-wayland-amd64` und `rust-wayland-arm64` wurden heruntergeladen und
zusätzlich mit `scripts/check-native-evidence.py` geprüft. Beide enthalten alle
acht Laufzeitmarkierungen, die NetworkManager-/BlueZ-Vertragsnachweise, den
1280×720-Screenshot und den Speicherwert.

| Kurzer Laufzeittest | amd64 | arm64 |
|---|---:|---:|
| Cgroup-Speicherspitze | 215,7 MiB | 162,7 MiB |
| Speicherlimit, ohne Swap | 1 GiB | 1 GiB |

Die Werte sind keine Langzeitlast- oder Raspberry-Pi-GPU-Messung.

Der bisherige CI-Lauf meldete grüne Jobs, obwohl die Log-Pipeline einen
Docker-Fehler beim Start der WebKit-Sandbox verdeckte. Die Artefaktprüfung hat
diesen unvollständigen Lauf abgewiesen. Sein grüner Gesamtstatus ist **kein**
Nachweis aller folgenden Schritte. Die korrigierte Pipeline verwendet `pipefail`
und prüft jede Laufzeitmarkierung sowie Speicherwert und Screenshot ausdrücklich.
Der nachfolgende Umfang ist lokal auf amd64 und in der oben verlinkten
korrigierten CI auf beiden Architekturen nachgewiesen. Die aktuelle Prüfung
weist die unvollständigen historischen Artefakte weiterhin ausdrücklich ab.

- Rust-Code mit `Cargo.lock` kompiliert; Formatierung und Clippy ohne Warnungen.
- Neun Rust-Core-Tests zu Konfiguration, Schreibrechten, URL-/Hostvalidierung,
  sicherer Befehlsübergabe, Kanban-Filtern und Wellenparametern.
- Tatsächlicher labwc-Compositor mit virtuellem Ausgang und Pixman-Renderer;
  GTK meldet `GdkWaylandDisplay`; ein App-Fenster, sechs Hauptmodule und sechs
  Einstellungsseiten. WLAN und Bluetooth sind getrennt.
- Tatsächlicher VTE-PTY-Rundlauf einschließlich Eingabe und dargestelltem Ergebnis.
- Tatsächliche WebKitGTK-Engine mit lokalem DOM und JavaScript-Ergebnis.
- Klick-Audio über die bestehende libcanberra-/PulseAudio-Ausgabe aufgenommen.
- Rust/GIO gegen eine isolierte NetworkManager-Fixture: Suche, persönliche
  Profilberechtigung, übergebener WLAN-Schlüssel, vorhandenes Profil wiederverwenden,
  Trennen sowie Radiozustand. Keine Funk-/WPA-Abnahme durch diese Fixture.
- Rust/GIO gegen eine isolierte BlueZ-Fixture: eigene Suchverbindung und ihre
  Freigabe, Adapterprüfung, Koppeln, Verbinden/Trennen, Vertrauen/Entziehen und
  Entfernen. Die tatsächliche GTK-Seite startet eine Suche; der Wechsel zum
  WLAN-Tab schließt deren D-Bus-Client. Es bleibt genau ein App-Fenster.
  Agent1-PIN/Passkey und echte Funkkopplung sind dadurch nicht abgenommen.
- ShellCheck für Installer und Sitzung; Screenshot als CI-Artefakt.
- Tatsächliche GTK-Kanban-Seite: Laden beim Öffnen, kombinierte Suche und drei
  unabhängige Filter, unveränderte Quelldatei, Aktualisierung nach einer externen
  Dateiänderung sowie Erhalt zuvor geladener Aufgaben bei ungültiger JSON-Quelle.

Der Laufzeitcontainer hat **1 GiB RAM, kein zusätzliches Swap** und vier virtuelle
CPUs. Er verwendet keine Host-Grafik- oder Eingabegeräte und kein Netzwerk.
Weder Xorg noch Xwayland noch `startx` laufen. Die WebKit-Sandbox bleibt aktiv;
Docker erlaubt für sie unprivilegierte User-Namespaces. Quelle und Buildvolume
sind während des Laufzeittests schreibgeschützt eingebunden.

Nicht nachgewiesen sind damit ein kompletter Raspberry-Pi-Boot, GPU-/HDMI-Leistung,
physische Audioqualität, Langzeitlast, neue Installer-/Login-Abläufe, echte
Rust-BlueZ-Kopplungen oder Verbindungen des neuen Wayland-Remote-Clients.
Die früheren Python-/QML- und QEMU-Ergebnisse werden nicht als Rust-Nachweise
übernommen. Physische Hardwaretests bleiben auf Nutzerwunsch ausgeschlossen.
