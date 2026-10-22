# Native Softwareabnahme: Einrichtung, Kopplung, Belastung und Installer

Geprüfter Programm-/Installer-Quellstand:
`ec7a88e65ab4aa9721fd3c68f3d29143f054e172`.

- [Rust-/Wayland-CI mit beiden Architekturen](https://github.com/jtracht/rampi-os/actions/runs/39870928396).
- [Alle sechs bisherigen CI-Jobs](https://github.com/jtracht/rampi-os/actions/runs/39870928431).

Die vollständigen Artefakte `rust-wayland-amd64` und `rust-wayland-arm64` wurden
nach dem erfolgreichen Lauf heruntergeladen und unabhängig erneut mit
`scripts/check-native-evidence.py` geprüft. ARM64 verwendet zusätzlich
`--require-installer`. Eine grüne Workflow-Anzeige allein gilt nicht als Nachweis.

## Tatsächliche grafische Anwendung

Die 14 Pflichtmarker belegen je Architektur dieselbe GTK-Anwendung auf einer
echten labwc-/Wayland-Sitzung mit Pixman/Cairo, 1280 × 720, einem Rampi-Fenster,
1 GiB Containerlimit und ohne Swap:

- Dashboard, sechs Module und sechs getrennte Einstellungsbereiche.
- Fortsetzbarer Assistent und mehrere persönliche Hostprofile einschließlich
  Validierung, Aktivierung, abgebrochener und bestätigter Entfernung.
- Tatsächliche Tastatureingabe über den vorhandenen Wayland-Eingabeweg.
- Eingabe/Ausgabe eines tatsächlichen VTE-PTYs sowie WebKit-DOM/JavaScript.
- Bluetooth-Seite und Freigabe ihrer eigenen Suche beim Tabwechsel.
- Agent1-Codevergleich, PIN-/Passkey-Antworten, Abbruch mit geleerter Eingabe und
  `AccessDenied` für einen fremden D-Bus-Absender desselben Unix-Benutzers.
- Lokales Kanban mit kombinierten Filtern, Aktualisierung und Fehlererhalt.
- WireGuard-Seite mit persönlicher Profilauswahl und tatsächlichen GTK-Aktionen.
- Tailscale-Seite mit dem Zustand des vorhandenen offiziellen Dienstes.
- Tatsächlich aufgezeichnete libcanberra-/Pulse-Klickausgabe.
- Längerer Seitenwechseltest und Ausschluss von Xorg/Xwayland/startx.

Zusätzlich wird auch in beiden CI-Architekturen der normale Start ohne Testargumente geprüft: Die
Einrichtungsseite erscheint, Tab/Enter wechseln zum nächsten Schritt und die
persönliche Datei enthält `setup_step=1` bei `setup_complete=false`.

## Messwerte unter dem Softwarelimit

600 überprüfte Seitenwechsel über mehr als drei Minuten, drei echte VTE-PTYs
und lokaler WebKit-Inhalt. Der Zeitwert für einen Wechsel stammt vom beobachteten
GTK-Zeichenereignis, nicht nur vom Aufruf einer Navigationsfunktion.

| Messwert | AMD64 | ARM64 |
|---|---:|---:|
| Start bis beobachtete Zeichenausgabe | 88,6 ms | 79,7 ms |
| 95. Perzentil Seitenwechsel | 19,1 ms | 18,4 ms |
| Rampi-Prozess, maximal beobachteter RSS | 281,6 MiB | 229,7 MiB |
| Gesamte Testlaufzeit, cgroup-Speicherspitze | 310,3 MiB | 230,9 MiB |
| Prozess-CPU während Wechseln, Anteil eines Kerns | 19,7 % | 18,2 % |
| Prozess-CPU mit reduzierter Bewegung im Ruheabschnitt | 0,36 % | 0,57 % |

Die Speicherprüfung vergleicht zusätzlich die residenten Werte nach der
Aufwärmphase und am Ende. Der Test erzwingt beobachtete Zeichenausgabe für jeden
Wechsel, vollständige JSON-Messwerte und die festgelegten Softwarebudgets.
Prozess-RSS und cgroup-Speicher sind unterschiedliche Messgrößen.

Diese Werte gelten für die jeweiligen CI-Rechner mit Softwaredarstellung. Sie
sind keine Pi-Geschwindigkeits-, GPU-, Video-Decodierungs- oder echte
Windows-/KI-Lastmessung. Physische Hardwaretests sind ausdrücklich ausgeschlossen.

## Dienste und reale Protokollprüfung

Private NetworkManager-/BlueZ-Testdienste prüfen die Produktionsadapter und die
grafischen Bedienabläufe. Sie simulieren keine erfolgreiche Funkverbindung als
Hardware-Nachweis. Separat importiert und aktiviert derselbe Rust-/libnm-Adapter
zwei tatsächliche NetworkManager-/Kernel-WireGuard-Gegenstellen. Verschlüsselter
Verkehr, falscher Schlüssel, Trennen und Linux-Benutzerisolation sind geprüft.

Die offizielle Tailscale-CLI mit einem isolierten tatsächlichen Dienst belegt
`NeedsLogin`. Gesonderte CLI-Fixtures prüfen fehlende Software, ungültige und zu
große Ausgaben sowie einen nach Zeitablauf beendeten Prozess. Eine Anmeldung oder
Tailscale-Tunnelverkehr wird damit nicht behauptet.

## ARM64-Installationsabläufe

`RAMPI_RUST_INSTALLER_LIFECYCLE_OK` stammt aus einem separaten wegwerfbaren
ARM64-Trixie-Container mit echten Paketen. Geprüft sind:

- Installation eines ausführbaren Rust-Programms mit seinen passenden Grafiken.
- Root-Besitz und Schreibschutz trotz gewöhnlichem Quellbesitz.
- Wiederholte Installation ohne Änderung des zuvor laufbaren Datei-Inodes.
- Atomare Aktivierung und funktionsfähiger Rückwechsel mit Prüfsummen.
- Ungültiges Installationsprogramm und nachträglich veränderte Rückwechselversion
  werden abgewiesen, die ausgewählte Version bleibt erhalten.
- Deinstallation erhält persönliche Daten und Versionsordner.
- Eigener unveränderter Greeter führt zurück zum TTY-Start; ein später gewählter
  fremder Login-Dienst und sein grafischer Start bleiben bestehen.

Der Test verwendet den Image-Modus ohne physische Modellerkennung. Er ist keine
grafische PAM-Login-Abnahme. Image-Bau und QEMU-Boot werden getrennt geprüft.
Zwölf Rust-Core-Tests bestehen auch unter Windows; die historischen 87
Python-Prototyp-Tests bleiben zusätzliche Regressionen und ersetzen keine native
Abnahme.
