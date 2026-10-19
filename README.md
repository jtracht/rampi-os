# Rampi OS

Native Remote-Arbeitsumgebung für Raspberry Pi 3 Model B+ und Windows 11 Pro.
Eigenständige Qt-Quick-Oberfläche; vorhandene Systemdienste übernehmen Netzwerk,
Login, Terminals, Remote Desktop und Browser. Eigenentwickelter Code: Apache-2.0.

**Status: Entwicklungsstand.** Die native Oberfläche, persönliche Konfiguration,
lokales Kanban und native Windows-ConPTY-Persistenz sind implementiert und getestet.
Die Abnahme erfolgt auf ausdrücklichen Nutzerwunsch ausschließlich softwareseitig:
ARM64-Docker, native Windows-CI und Image-/QEMU-Prüfungen. Physische Hardwaretests
sind aus dem Umfang ausgeschlossen. [Funktionsstand](docs/STATUS.md) und
[Testnachweise](docs/TESTING.md) nennen die tatsächlichen Ergebnisse und Grenzen.

## Start auf einem Entwicklungsrechner

Python 3.11 oder neuer:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\rampi --windowed
```

Unter Linux dieselben Python-Befehle mit `.venv/bin/python` beziehungsweise
`.venv/bin/rampi` ausführen. Ohne Linux-Dienste bleibt das Dashboard nutzbar und
zeigt deren tatsächliche Nichtverfügbarkeit. Es werden keine Demo-Verbindungen
oder laufenden KI-Sitzungen vorgetäuscht.

## Raspberry Pi

Raspberry Pi OS Lite Trixie **arm64**, Ziel Pi 3 B+, 1 GB RAM:

```sh
./setup.sh --check
sudo ./setup.sh --install
# Optional vorhandene Tailscale-/Moonlight-Installationen erkennen, sonst ergänzen:
sudo ./setup.sh --install --with-extras
```

Im vorhandenen Anmeldebildschirm die Sitzung **Rampi** wählen. Das Skript prüft
Pakete, verändert keine Firmwareeinstellungen und ersetzt keine vorhandenen
Netzwerkmanager. Bei einem aktiven konkurrierenden Netzwerkmanager stoppt es.
[Installation](docs/INSTALL-RASPBERRYPI.md)

## Windows-Host

```powershell
.\setup.ps1                  # Bestandsaufnahme, keine Systemänderung
.\setup.ps1 -Install         # Nur persönlicher Sitzungsadapter
```

OpenSSH, RDP und fehlendes psmux werden ausschließlich über ausdrückliche Optionen
eingerichtet. Die offiziellen Anbieter-CLIs behalten ihre eigene Anmeldung und
Sicherheitsdialoge. [Windows-Einrichtung](docs/INSTALL-WINDOWS11.md)

## Bedienung

- Pfeiltasten: Kachelauswahl; Enter: öffnen; Tab: weitere Bedienelemente.
- Strg+Alt+Pos1: Dashboard über den bestehenden Window-Manager.
- Alt+Tab: laufende Anwendungen wechseln; Escape: zurück im Dashboard.
- Strg+Komma: Einstellungen; F11: Vollbild im Client.
- Strg+Alt+F2: reguläre Linux-Systemkonsole.

Kanban ist schreibgeschützt. Browser und KI-Terminals starten erst bei Bedarf.
Updates erfolgen ausschließlich durch manuelle Ausführung der Update-Skripte.

## Entwicklung und Auslieferung

```sh
pytest -q
ruff check client tests scripts
mypy client/rampi
python -m rampi.app --smoke-test
python scripts/package.py
```

GitHub Actions prüft Linux/Windows, Skripte, Sicherheit und die Paketierung.
Der Image-Workflow verwendet einen festgelegten Commit des offiziellen pi-gen.
Reguläre Releases bleiben bis zur dokumentierten Softwareabnahme gesperrt;
Release Please bereitet danach Versionen, Tags und zunächst unveröffentlichte
Releases vor. Veröffentlichung erfolgt erst nach vollständigem Image-Build.

Die [Dashboard-Vorlage](assets/references/1000141105.png) und das
[gelieferte Logo](assets/references/1000141106.png) sind die Designgrundlage.
Ihre Rechte sind separat in [RIGHTS.md](assets/references/RIGHTS.md) dokumentiert.
Rampi ist ein unabhängiges Projekt. Raspberry Pi is a trademark of Raspberry Pi Ltd.

Weitere Dokumentation: [Architektur](docs/ARCHITECTURE.md),
[bestehende Dienste](docs/EXISTING-SERVICES.md),
[Konfiguration](docs/CONFIGURATION.md), [Tests](docs/TESTING.md),
[Image-Build](docs/IMAGE-BUILD.md), [Release-Prozess](docs/RELEASING.md).
