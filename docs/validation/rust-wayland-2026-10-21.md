# Rust-/Wayland-Nachweis vom 21. Oktober 2026

Revision: `3788dc1`, Entwicklungszweig `codex/software-acceptance-85`.
Die Umstellung ist noch kein regulärer Release.

[Rust-/Wayland-CI](https://github.com/jtracht/rampi-os/actions/runs/39512410403)
hat die nativen Jobs für **amd64 und arm64 erfolgreich** abgeschlossen:

- Rust-Code mit `Cargo.lock` kompiliert; Formatierung und Clippy ohne Warnungen.
- Acht Rust-Core-Tests zu Konfiguration, Schreibrechten, URL-/Hostvalidierung,
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
- ShellCheck für Installer und Sitzung; Screenshot als CI-Artefakt.

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
