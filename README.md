# Rampi OS

Native Remote-Arbeitsumgebung für Raspberry Pi 3 Model B+ und Windows 11 Pro.
Die native Anwendung und ihre Oberfläche verwenden **Rust / GTK 4 / Wayland**.
Die neue Sitzung verwendet labwc und benötigt kein `startx`. Terminals und Browser
werden über VTE und WebKitGTK integriert. Netzwerk und Anmeldung verwenden
weiterhin vorhandene Systemdienste. Eigenentwickelter Code: Apache-2.0.

**Aktuell: 95,8 % (91/95 Punkte im Drei-Modul-Umfang); native Vorabversion.**
Bewertung, Abnahmen und offene Arbeiten stehen in [PROGRESS.md](docs/PROGRESS.md).
Die [Migrationsübersicht](docs/RUST-MIGRATION.md) nennt Quellcode, Start,
softwareseitige Nachweise und verbleibende Funktionen. Der frühere Stand von
ca. 75 % gehört zum Python-/QML-Prototyp; er wird nicht als Fertigstellungsgrad
der neuen Rust-Laufzeit ausgegeben. Die aktuellen [Fortschrittswerte](docs/PROGRESS.md)
werden deshalb gesondert bewertet.

Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen. Rust wird mit
Docker/Wayland, nativer ARM64-CI und anschließend neuen Image-/QEMU-Tests geprüft.

Rampi umfasst drei Hauptmodule: **Kanban**, **Remote Desktop** und **Browser**.
[v0.6.0-dev.5](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.5) enthält das frisch gebaute native ARM64-Image
mit Streaming, RDP, persönlichen PAM-Schlüsselbünden und DE-/EN-Sitzungssprache.
Beide Erstkonto-Wege und jeweils ein normaler Neustart bestehen; alle
28 öffentlichen Dateien wurden unabhängig heruntergeladen und geprüft:
[Release-Abnahme](docs/validation/native-dev5-keyboard-release.md).

Beim ersten Start wird ein eigener Benutzer mit eigenem Kennwort eingerichtet;
es gibt kein Standardpasswort. Ältere Releases werden nicht überschrieben.
Die verbleibenden Abnahmegrenzen stehen im Fortschrittsbericht; das Release
bleibt ausdrücklich eine Vorabversion.

## Rust-Entwicklung unter Linux

```sh
cargo test --locked -p rampi-core
RAMPI_ASSETS="$PWD/client/rampi" cargo run --locked -p rampi-ui -- --windowed
```

GTK-/VTE-/WebKitGTK-Entwicklungspakete werden benötigt. Der gesamte Docker-
Prüflauf ist mit `python scripts/test-native.py` wiederholbar; er friert Quellen
und Programm für die Prüfung ein. [Entwicklung](docs/NATIVE-DEVELOPMENT.de.md),
[Bedienung](docs/NATIVE-USER-GUIDE.de.md), [Umfang und Fehlerhilfe](docs/NATIVE-SUPPORT.de.md).

## Historischer Python-/QML-Prototyp

Python 3.11 oder neuer:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\rampi --windowed
```

Unter Linux dieselben Python-Befehle mit `.venv/bin/python` beziehungsweise
`.venv/bin/rampi` ausführen. Ohne Linux-Dienste bleibt das Dashboard nutzbar und
zeigt deren tatsächliche Nichtverfügbarkeit. Es werden keine Demo-Verbindungen
vorgetäuscht.

## Raspberry Pi

Raspberry Pi OS Lite Trixie **arm64**, Ziel Pi 3 B+, 1 GB RAM:
Der native Checkout benötigt ein dazu gebautes ARM64-Programm unter
`native/bin/rampi-native` oder über `RAMPI_NATIVE_BINARY`.
[Nativer Betriebsleitfaden](docs/NATIVE-OPERATIONS.de.md).

```sh
./setup.sh --check
sudo ./setup.sh --install
```

Der native Installer verwendet eine kompatible vorhandene Moonlight-C-Bibliothek
oder baut ausschließlich das offizielle Bibliotheksziel. Ein externer Player ist
für das integrierte Streaming nicht erforderlich.

Im vorhandenen Anmeldebildschirm die Sitzung **Rampi** wählen. Das Skript prüft
Pakete, verändert keine Firmwareeinstellungen und ersetzt keine vorhandenen
Netzwerkmanager. Bei einem aktiven konkurrierenden Netzwerkmanager stoppt es.
[Installation](docs/INSTALL-RASPBERRYPI.md)

## Windows-Host

```powershell
.\setup.ps1                  # Bestandsaufnahme, keine Systemänderung
.\setup.ps1 -EnableRdp       # RDP ausdrücklich aktivieren (erhöhte PowerShell)
```

OpenSSH und RDP werden ausschließlich über ausdrückliche Optionen eingerichtet.
Direkte KI-Module und der zusätzliche Windows-Sitzungsadapter wurden auf
Nutzerwunsch entfernt. [Windows-Einrichtung](docs/INSTALL-WINDOWS11.md)

## Bedienung

- Pfeiltasten: Kachelauswahl; Enter: öffnen; Tab: weitere Bedienelemente.
- Strg+Alt+Pos1: Dashboard über labwc; das Kürzel erreicht die Terminal-PTY nicht.
- Escape: zurück auf Rampi-Seiten; im Terminal und Browser bleibt es für diese nutzbar.
- Strg+Alt+F2: reguläre Linux-Systemkonsole.

Kanban ist schreibgeschützt. Browser und lokale Systemkonsole starten erst bei Bedarf.
Updates erfolgen ausschließlich durch manuelle Ausführung der Update-Skripte.
Kanban kombiniert Suche mit Projekt-, Prioritäts- und Statusfiltern. Die
Spaltenreihenfolge lässt sich in den Einstellungen ändern; zusätzliche Statuswerte
bleiben sichtbar. Die VPN-Seite bietet eine Auswahl persönlicher WireGuard-Profile
mit tatsächlichem Verbindungszustand.

Unter **Einstellungen → Host & SSH** lassen sich mehrere persönliche Hosts
verwalten und aktivieren, OpenSSH-Schlüssel erzeugen und unabhängig geprüfte
Hostfingerprints übernehmen. Für RDP wird kein Rampi-Adapter auf Windows benötigt.
WLAN, Bluetooth und VPN haben eigene integrierte Einstellungsseiten. System bietet
persönliche Tastaturbelegung, Auflösungen mit Rücksetzung, Kennwort und Abmeldung.
WebKit-Downloads und Webseitenabfragen bleiben innerhalb der Rampi-Anwendung.
RDP und Desktop-Streaming verwenden eingebettete GTK-Flächen im vorhandenen Fenster.
Streaming verwendet die vorhandenen Moonlight-/GStreamer-Bibliotheken und persönliche
Schlüsselbünde. Die freigegebenen Workflows und Release-Artefakte enthalten die
Nachweise des jeweiligen unveränderlichen Versionsstands.

## Historische Regression und Auslieferung

```sh
pytest -q
ruff check client tests scripts
mypy client/rampi
python -m rampi.app --smoke-test
python scripts/package.py
```

GitHub Actions prüft Linux/Windows, Skripte, Sicherheit und die Paketierung.
Der Image-Workflow verwendet einen festgelegten Commit des offiziellen pi-gen.
Die dokumentierte Softwareabnahme erlaubt die Releasevorbereitung;
der native Release-Workflow verlangt eine abgestimmte stabile Version und erzeugt
das Tag erst nach erfolgreichem frischem Image-Build und vollständiger Abnahme.
Die veröffentlichten Dateien werden anschließend separat heruntergeladen und geprüft.

Die [Dashboard-Vorlage](assets/references/1000141105.png) und das
[gelieferte Logo](assets/references/1000141106.png) sind die Designgrundlage.
Ihre Rechte sind separat in [RIGHTS.md](assets/references/RIGHTS.md) dokumentiert.
Rampi ist ein unabhängiges Projekt. Raspberry Pi is a trademark of Raspberry Pi Ltd.

Weitere Dokumentation: [Architektur](docs/ARCHITECTURE.md),
[bestehende Dienste](docs/EXISTING-SERVICES.md),
[Konfiguration](docs/CONFIGURATION.md), [Tests](docs/TESTING.md),
[Image-Build](docs/IMAGE-BUILD.md), [Release-Prozess](docs/RELEASING.md).
