# RAMPI OS – CODEX-MASTERPROMPT V3.1
## Vollständige Entwicklung, Nutzung bestehender Systemdienste, GitHub-Repository, automatisierte CI/CD-Pipelines und Releases

### 1. Rolle und Mission

Du bist ein interdisziplinäres Senior-Entwicklungsteam mit Expertise in:

- Embedded Linux und Raspberry Pi
- Windows 11 Pro und nativer Windows-Entwicklung
- Systemarchitektur, C/C++ und Full-Stack-Entwicklung
- Linux-Systemdiensten, D-Bus, systemd und PAM
- Netzwerkadministration, VPN, SSH und Remote Desktop
- Cybersecurity und Benutzerisolation
- UI/UX, Motion Design und Grafikgestaltung
- DevOps, Git, GitHub Actions und Release Engineering
- Softwarequalität, Performanceoptimierung und Testing

Entwickle **Rampi OS**, eine eigenständige, hochperformante Remote-Workstation für den Raspberry Pi 3 Model B+ mit Windows 11 Pro als zunächst unterstütztem Hostbetriebssystem.

Erstelle tatsächliche, funktionsfähige Software, keine bloßen Konzepte, Simulationen oder Mockups.

Die Entwicklung umfasst den vollständigen Quellcode, die grafische Oberfläche, native Integrationen, Installationsskripte, ein öffentliches GitHub-Repository, automatisierte CI/CD-Pipelines, Release-Tags, ein flashbares Systemimage und eine vollständige Dokumentation.

Arbeite eigenständig und triff technische Standardentscheidungen nach überprüfbaren Kriterien.

Alle bereits festgelegten Produktentscheidungen sind verbindlich.

---

# 2. Oberstes Entwicklungsprinzip: Vorhandenes verwenden

**Dieses Kapitel ist eine verbindliche Vorgabe und gilt für alle Komponenten von Rampi OS.**

## 2.1 Keine unnötigen Eigenentwicklungen

Verwende vorhandene, bewährte, aktiv gepflegte Dienste, Programme, Systemfunktionen, Bibliotheken, APIs und Protokolle, wann immer diese die Anforderungen zuverlässig erfüllen.

Entwickle keine eigenen Alternativen zu bestehenden, geeigneten Lösungen.

Insbesondere sollen keine eigenen Implementierungen entwickelt werden für:

- WLAN- und Netzwerkprotokolle
- Bluetooth-Protokolle und Pairing
- VPN-Protokolle
- SSH-Protokolle
- Remote-Desktop-Protokolle
- Vollständige Browser-Engines
- Allgemeine Fenstermanager oder Display-Server
- Linux-Benutzerauthentifizierung
- Verschlüsselungsalgorithmen
- Paketverwaltung
- Grundlegende Systemdienstverwaltung
- Bereits vorhandene Terminal-Engines
- Verfügbare und geeignete Systemdiagnosefunktionen

Verwende ausschließlich dann Eigenentwicklungen, wenn bestehende Lösungen die konkreten Anforderungen nicht ausreichend erfüllen oder eine Rampi-spezifische Integration notwendig ist.

Bevor eine neue Komponente entwickelt wird, prüfe, ob eine geeignete bestehende Lösung vorhanden ist.

## 2.2 Vorhandene Installationen erkennen

Prüfe vor jeder Installation, ob die erforderliche Software bereits installiert und korrekt konfiguriert ist.

Unter Linux beispielsweise über:

- Paketverwaltung und Paketdatenbank
- `systemctl`
- D-Bus
- Erkennung vorhandener ausführbarer Programme
- Programmversionsprüfungen
- Vorhandene Konfigurationsdateien
- Erreichbarkeit bestehender Dienste

Unter Windows beispielsweise über:

- PowerShell
- `Get-Command`
- `Get-Service`
- Windows Features und Capabilities
- Windows-Registrierung, wo erforderlich
- Installierte Programme
- `winget`, soweit vorhanden und geeignet
- Vorhandene Dienste und Konfigurationen

Ist eine kompatible Komponente bereits vorhanden, verwende sie.

Installiere keine zweite Instanz derselben Funktion, sofern dies keinen zwingenden technischen Grund hat.

Verhindere konkurrierende Dienste.

Bestehende funktionierende Konfigurationen müssen grundsätzlich erhalten bleiben.

## 2.3 Bevorzugte Integrationsstrategie

Nutze vorhandene Komponenten in dieser Priorität:

1. Vorhandene und kompatible Systemfunktionen
2. Bereits installierte, geeignete Programme
3. Offizielle Schnittstellen und Bibliotheken
4. Etablierte, aktiv gepflegte Open-Source-Lösungen
5. Eigene schlanke Rampi-Adapter
6. Eigene Implementierung, ausschließlich bei tatsächlicher Notwendigkeit

Ein bereits installiertes Programm hat keinen automatischen Vorrang, wenn es veraltet, unsicher, inkompatibel oder ungeeignet ist.

Jede verwendete Lösung muss technisch geeignet und rechtlich zulässig sein.

## 2.4 Konkrete bevorzugte Dienste und Programme

| Funktion | Bevorzugte bestehende Lösung |
|---|---|
| Linux-Dienste | systemd |
| Benutzeranmeldung | Linux-PAM |
| Benutzerverwaltung | Linux-Systemkonten |
| Berechtigungen | Linux-Rechte, Gruppen und polkit |
| WLAN | NetworkManager |
| WLAN-Schnittstelle | NetworkManager D-Bus |
| Bluetooth | BlueZ |
| Bluetooth-Schnittstelle | BlueZ D-Bus |
| VPN | Tailscale |
| Eigenständiges VPN | WireGuard |
| SSH auf Raspberry Pi | OpenSSH |
| SSH auf Windows | Windows OpenSSH Server |
| RDP-Client | FreeRDP |
| RDP-Host | Microsoft Remote Desktop unter Windows 11 Pro |
| Desktop-Streaming-Host | Sunshine |
| Streaming-Client | Moonlight, falls auf Pi 3 B+ kompatibel |
| Terminaldarstellung | Geeignete vorhandene Terminalbibliothek |
| Windows-Terminals | ConPTY und unterstützte native Schnittstellen |
| Bootanimation | Plymouth, falls geeignet |
| Browser | Vorhandener geeigneter ARM-Linux-Browser |
| KI-Integration | Offizielle Anbieter-CLIs |
| Git | Git |
| CI/CD | GitHub Actions |
| Versionierung | Semantic Versioning und Conventional Commits |
| Systemimage | Geeignete Raspberry-Pi-Image-Build-Werkzeuge |

Diese Tabelle beschreibt bevorzugte Integrationskandidaten, keine ungeprüfte Verpflichtung, inkompatible Software einzusetzen.

Prüfe die tatsächliche Unterstützung der Zielhardware und des Zielbetriebssystems.

## 2.5 Nur Rampi-spezifische Funktionen selbst entwickeln

Die Eigenentwicklung konzentriert sich auf:

- Das Rampi-Dashboard
- Die grafische Benutzeroberfläche
- Das Rampi-Designsystem
- Flüssige Auswahlanimationen
- Tastaturnavigation
- Modulwechsel und Vollbildsteuerung
- Einheitliche Einstellungsoberflächen
- Setup-Assistent
- Zustandsverwaltung
- Benutzerbezogene Konfigurationen
- Integration vorhandener Dienste
- Einheitliche Fehlerbehandlung
- Kanban-Anzeige und notwendige Datenadapter
- KI-Terminalverwaltung
- Notwendige Sitzungsvermittlung zwischen Windows und Rampi
- Systemstatus und Diagnoseoberflächen

Auch hier sollen geeignete Bibliotheken und Frameworks verwendet werden.

**Entwickle möglichst wenig eigenen infrastrukturellen Code, aber eine möglichst hochwertige eigene Benutzeroberfläche.**

---

# 3. Produktvision

Rampi bedeutet **Remote Raspberry Pi**.

Rampi ist eine eigenständige, moderne grafische Arbeitsumgebung für den Raspberry Pi 3 Model B+.

Der Raspberry Pi wird über HDMI an einen Bildschirm oder Beamer angeschlossen.

Die Bedienung erfolgt mit einer Bluetooth-Tastatur sowie einer Bluetooth- oder USB-Maus.

Ziel ist ein modernes, besonders ressourcenschonendes System, das Entwicklerwerkzeuge und eine Windows-Remote-Workstation in einer einheitlichen Oberfläche vereint.

Es gibt sechs Hauptmodule:

1. **Kanban Board:** Grafische, schreibgeschützte Aufgabenübersicht
2. **ChatGPT / Codex:** Interaktive native Windows-Codex-CLI
3. **Claude / Claude Code:** Interaktive native Windows-Claude-Code-CLI
4. **Gemini / Antigravity:** Offiziell unterstützte native Windows-Antigravity-CLI
5. **Remote Desktop:** Windows-Desktop-Streaming und RDP
6. **Webbrowser:** Performanter lokaler Browser

Jedes Modul ist einzeln im Vollbild nutzbar.

Zwischen den Modulen kann jederzeit gewechselt werden.

Das Dashboard muss auch ohne erreichbaren Windows-Laptop funktionieren.

Die eigentliche KI-Verarbeitung erfolgt auf dem Windows-Host.

---

# 4. Verbindliche strategische Entscheidungen

Alle 15 bisher getroffenen Entscheidungen bleiben unverändert.

| Nr. | Bereich | Festlegung |
|---|---|---|
| 1 | Host-Verfügbarkeit | Windows-Laptop eingeschaltet und geöffnet |
| 2 | Architektur | Erweiterbar auf mehrere Hosts, zunächst Windows 11 |
| 3 | VPN | Tailscale und eigenständiges WireGuard gleichberechtigt |
| 4 | Benutzerverwaltung | Native Linux-Systembenutzer |
| 5 | Benutzerdaten | Vollständig getrennte persönliche Konfigurationen |
| 6 | KI-Sitzungen | Persistent auf Windows, auch bei Rampi-Verbindungsabbrüchen |
| 7 | KI-Ausführung | Nativ unter Windows, kein WSL2-Zwang |
| 8 | Remote Desktop | Desktop-Streaming und RDP vollständig unterstützt |
| 9 | Windows-Edition | Windows 11 Pro |
| 10 | Konten | Eigene Windows-Konten, SSH-Schlüssel und Zugänge je Benutzer |
| 11 | Oberfläche | Eigenständige schlanke grafische Rampi-Sitzung |
| 12 | Installation | Installer auf Raspberry Pi OS Lite und eigenes Systemimage |
| 13 | Updates | Ausschließlich manuelle Installation von Updates |
| 14 | Quellcode | Vollständig Open Source |
| 15 | Lizenz | Apache License 2.0 für den eigenentwickelten Code |

Zusätzlich verbindlich:

- Öffentliches GitHub-Repository
- Automatisierte CI/CD-Pipelines
- Automatische Git-Tags
- Automatisch veröffentlichte GitHub-Releases
- Flashbares Raspberry-Pi-Image pro regulärem Release
- `setup.sh` als Release-Artefakt
- `setup.ps1` und Windows-Hostpaket als Release-Artefakte
- Automatisierte Tests
- Ausführliche Dokumentation
- Nutzung der beigefügten Design- und Logo-Referenzen
- Konsequente Wiederverwendung vorhandener Systemdienste und Programme

---

# 5. Verbindliche Designreferenzen

Dem Auftrag sind zwei Bilder beigefügt.

Diese sind bei der tatsächlichen Entwicklung zu verwenden.

## Dashboard-Referenz

**Datei:** `1000141105.png`

Übernimm die grundlegende Anordnung und visuelle Gestaltung:

- Rampi-Branding links oben
- Statusinformationen rechts oben
- Sechs große farbige Hauptkacheln
- Kanban-Vorschau
- Vorschauen der KI-Module
- Untere Systemleiste
- Einstellungen links unten
- Dunkler, minimalistischer Hintergrund
- Große, gut lesbare Typografie
- Moderne Icon-Sprache

Die Oberfläche soll der Vorlage hinsichtlich visueller Qualität, Anordnung, Proportionen und Designcharakter möglichst nahekommen.

Verwende das Bild nicht nur als lose Inspiration.

## Logo-Referenz

**Datei:** `1000141106.png`

Verwende das bereitgestellte Rampi-Logo.

Seine charakteristischen Bestandteile sind:

- Grüne Blätter
- Rote Raspberry-Pi-Frucht
- Rote Funkwellen
- Rampi-Schriftzug

Erstelle daraus die notwendigen technischen Varianten:

- SVG, sofern sinnvoll rekonstruierbar
- PNG mit Transparenz
- Logo mit Schriftzug
- Kompaktes Symbol
- Bootscreen-Logo
- Login-Logo
- App-Icon
- Repository-Branding

Das ursprüngliche Logo und seine grundlegende Identität sollen erhalten bleiben.

Prüfe die Rechte an den gelieferten Grafiken und enthaltenen Drittanbieterkennzeichen vor der öffentlichen Weitergabe.

---

# 6. Grafische Gestaltung und Animationen

Verwende:

- Dunklen, beinahe schwarzen Hintergrund
- Intensive, klare Flächenfarben
- Minimalistische Komponenten
- Große abgerundete Kacheln
- Sehr wenige Rahmen
- Keine Farbverläufe
- Keine unnötigen Schatten
- Hochwertige Typografie
- Einheitliche Icons

Akzentfarben:

- Kanban: Korallrot
- Codex: Blau
- Claude: Gelb
- Gemini: Türkis
- Remote Desktop: Violett
- Browser: Dunkelblau
- Erfolgszustände: Grün

## Flüssige Auswahl

Beim Wechsel einer Auswahl soll die ausgewählte Fläche organisch reagieren.

Die Oberfläche soll wirken, als bestünde sie aus einer beweglichen Flüssigkeit.

Die Bewegung muss an allen vier Kanten sichtbar sein, einschließlich Ober- und Unterkante.

Es darf kein zusätzlicher Fokusrahmen verwendet werden.

Die aktive Farbe der ausgewählten Fläche verändert sich direkt.

Die Animationen sollen kurz und natürlich sein, anfangs ungefähr 120 bis 220 Millisekunden.

Nutze vorhandene effiziente Rendering- und Animationsmöglichkeiten.

Entwickle keine eigene Grafik-Engine, wenn eine vorhandene Bibliothek den Effekt performant erzeugen kann.

---

# 7. Tastatur- und Maussteuerung

Das gesamte System muss vollständig tastaturbedienbar sein.

Das betrifft auch:

- Login
- Setup-Assistent
- WLAN-Passworteingabe
- Bluetooth-Pairing
- VPN-Konfiguration
- Windows-Hosteinrichtung
- Einstellungen
- Kanban
- KI-Terminals
- Browser
- Remote Desktop

Navigation über Pfeiltasten, Enter, Escape, Tab und geeignete globale Tastenkombinationen.

Beim Wechsel auf die Tastatursteuerung verschwindet der Mauszeiger automatisch.

Bei erneuter Mausbewegung erscheint er wieder.

Verwende vorhandene Eingabe- und Fokusverwaltung des Grafikframeworks beziehungsweise Compositors.

Implementiere keine eigene Tastaturtreiber- oder Eingabegeräteschicht.

Reservierte Rampi-Tastenkombinationen dürfen nicht unbeabsichtigt an die Windows-Remote-Sitzung weitergeleitet werden.

---

# 8. Raspberry-Pi-Systemarchitektur

Verwende ein aktuelles, unterstütztes Raspberry Pi OS Lite als Systembasis.

Prüfe dessen tatsächliche Kompatibilität mit dem Raspberry Pi 3 B+.

Wähle eine schlanke grafische Umgebung.

Nutze einen bestehenden geeigneten Display-Server und Compositor beziehungsweise Fenstermanager.

Entwickle keinen eigenen Display-Server oder Fenstermanager, solange ein vorhandener die Anforderungen erfüllt.

Vermeide vollständige Desktopumgebungen.

Prüfe unter anderem:

- X11
- Wayland
- Schlanke Window-Manager
- Schlanke Compositoren
- GTK
- Qt
- SDL
- Geeignete native UI-Bibliotheken

Entscheide anhand von:

- RAM-Verbrauch
- GPU-Unterstützung
- CPU-Auslastung
- Remote-Desktop-Kompatibilität
- Stabilität
- Wartbarkeit
- Animationsleistung

Das Gesamtsystem muss auf 1 GB RAM sinnvoll nutzbar sein.

Starte Anwendungen bedarfsgerecht.

Vermeide doppelte Display-Server und fehlerhafte virtuelle Terminalbelegungen.

Ändere vorhandene Boot- und Display-Konfigurationen nur bei nachgewiesener Notwendigkeit.

---

# 9. Native Linux-Systemintegration

## Benutzer und Login

Nutze Linux-PAM und Linux-Systemkonten.

Keine separate Rampi-Benutzerdatenbank.

Speichere benutzerbezogene Einstellungen beispielsweise unter:

- `~/.config/rampi/`
- `~/.local/share/rampi/`
- `~/.cache/rampi/`

Jeder Benutzer besitzt eigene:

- Einstellungen
- Windows-Konten
- SSH-Schlüssel
- KI-Sitzungen
- Kanban-Verbindungen
- Browserprofile
- VPN-Profile
- Persönliche Zugangsdaten

Nutze vorhandene Linux-Rechte und geeignete sichere Secret-Speicher.

## WLAN

Verwende NetworkManager.

Nutze bevorzugt seine D-Bus-Schnittstellen.

Entwickle keine eigene WLAN-Verwaltung auf Protokollebene.

Rampi stellt ausschließlich die eigene grafische Bedienoberfläche bereit.

Alle Netzwerkoperationen müssen asynchron erfolgen.

## Bluetooth

Verwende BlueZ.

Nutze die bestehenden Pairing- und Verbindungsmechanismen.

Implementiere nur die grafische Verwaltung und notwendige Integrationslogik.

## Systemdienste

Verwende systemd.

Nutze vorhandene Funktionen für:

- Dienststart
- Autostart
- Neustart bei Fehlern
- Abhängigkeiten
- Logging
- Dienststatus
- Prozessüberwachung

Entwickle keinen eigenen allgemeinen Dienstmanager.

## Bootanimation

Prüfe Plymouth als bevorzugte bestehende Lösung.

Verwende dort die Rampi-Grafiken.

Vermeide die Neuentwicklung eines eigenen Bootsystems.

## Systemkonsole

Erhalte den regulären Linux-TTY-Zugang.

Stelle zusätzlich einen Zugriff aus den Rampi-Einstellungen bereit.

---

# 10. VPN und Fernvernetzung

Implementiere zwei gleichberechtigte VPN-Varianten.

## Tailscale

Verwende die vorhandene offizielle Tailscale-Software und ihre unterstützten Verwaltungsfunktionen.

Rampi übernimmt:

- Grafische Einrichtung
- Authentifizierung
- Statusanzeige
- Verbinden
- Trennen
- Wiederverbindung
- Fehleranzeige

## WireGuard

Verwende die vorhandenen WireGuard-Komponenten des Betriebssystems.

Unterstütze:

- Eigene Konfigurationen
- Konfigurationsimport
- Schlüsselverwaltung
- Verbindungsstatus
- Verbindungsaufbau
- Trennen
- Diagnose

Verwende keine eigene WireGuard-Protokollimplementierung.

Berücksichtige, dass VPN-Routing systemweite Auswirkungen haben kann.

Trenne Benutzerrechte und persönliche Profile korrekt.

---

# 11. Windows-11-Hostintegration

Verwende Windows 11 Pro als initiales Hostsystem.

Erstelle eine kleine, sichere Rampi-Hostintegration, die vorhandene Windows-Dienste bevorzugt verwendet.

## OpenSSH

Nutze den offiziellen Windows OpenSSH Server.

Prüfe, ob dieser bereits installiert und eingerichtet ist.

Übernimm funktionierende Konfigurationen, sofern sie sicher und kompatibel sind.

## Benutzerkonten

Jeder Rampi-Benutzer verwendet eigene Windows-Anmeldedaten und eigene SSH-Schlüssel.

Die tatsächlichen Windows-Berechtigungen sind verbindlich.

## Persistente KI-Sitzungen

Codex, Claude Code und Antigravity laufen nativ unter Windows.

Die Prozesse müssen bei Rampi-Modulwechsel, Rampi-Abmeldung und SSH-/VPN-Unterbrechungen weiterlaufen können.

Prüfe zuerst vorhandene zuverlässige Windows-native Lösungen für persistente Terminals und Sitzungskopplung.

Nutze bestehende APIs, Prozessverwaltungsmechanismen und ConPTY.

Nur wenn keine geeignete vorhandene Lösung die Anforderungen erfüllt, entwickle einen kleinen, abgesicherten Windows-Session-Broker.

Dieser darf nicht mehr Funktionen als nötig implementieren.

Die Benutzeridentität und Sitzungszugehörigkeit müssen überprüft werden.

Einfaches SSH ohne tatsächliche Sitzungspersistenz reicht nicht aus.

Keine WSL2-Pflicht.

Ein Neustart des Windows-Hosts muss laufende Prozesse nicht erhalten.

---

# 12. KI-Terminals

Verwende die offiziellen CLI-Programme der jeweiligen Anbieter.

## Codex

- Native Windows-Codex-CLI
- Interaktives Terminal
- Projektauswahl
- Wiederaufnahme unterstützter Sitzungen
- Benutzerberechtigungen
- Persistente hostseitige Prozesse

## Claude Code

- Native Windows-Claude-Code-CLI
- Interaktive Bedienung
- Projektverzeichnisse
- Sitzungsverwaltung
- Berechtigungsdialoge
- Hintergrundverarbeitung

## Gemini / Antigravity

- Offizielle unterstützte Antigravity-CLI
- Native Windows-Integration
- Interaktive Bedienung
- Projekte und Sitzungen
- Fehlerdiagnose

Überprüfe jeweils die aktuelle Anbieterunterstützung.

Erfinde keine nicht vorhandenen CLI-Funktionen.

Nutze eine gemeinsame bestehende Terminalbibliothek für die grafische Darstellung.

Die KI-Anwendungen behalten ihre offiziellen Authentifizierungs- und Sicherheitsmechanismen.

---

# 13. Remote Desktop

Unterstütze zwei Verfahren.

## Desktop-Streaming

Bevorzugt:

- Sunshine auf Windows
- Moonlight auf dem Raspberry Pi

Prüfe die tatsächliche Pi-3-B+-Kompatibilität einschließlich Videodecodierung und Grafiktreiber.

Wenn diese Kombination nicht zuverlässig funktioniert, integriere eine andere vorhandene, unterstützte Streaminglösung.

Entwickle kein eigenes Streamingprotokoll.

## RDP

Verwende Microsoft RDP unter Windows 11 Pro.

Auf dem Raspberry Pi soll ein geeigneter bestehender Client eingesetzt werden, bevorzugt FreeRDP.

Rampi übernimmt die grafische Konfiguration und Einbettung beziehungsweise Steuerung des Clients.

Berücksichtige die Windows-Einschränkungen hinsichtlich paralleler interaktiver Sitzungen.

Beide Remote-Verfahren müssen über persönliche Verbindungsprofile konfigurierbar sein.

---

# 14. Kanban-Board

Implementiere ein grafisches, schreibgeschütztes Kanban-Modul.

Funktionen:

- Projektübersicht
- Konfigurierbare Spalten
- Aufgabentitel
- Beschreibungen
- Prioritäten
- Status
- Filter
- Suche
- Offline-Cache

Keine Aufgaben erstellen, verändern, verschieben oder löschen.

Nutze offizielle APIs und vorhandene geeignete API-Bibliotheken.

Unterstütze über ein erweiterbares Connector-System:

- GitHub Projects
- Trello
- Jira
- Asana
- Notion
- Lokale JSON-Dateien

Jede Integration muss tatsächlich funktionieren, bevor sie als unterstützt ausgewiesen wird.

Verwende möglichst eingeschränkte Lesezugriffsrechte.

---

# 15. Webbrowser

Nutze einen bestehenden geeigneten Browser beziehungsweise eine vorhandene Browser-Engine.

Entwickle keinen eigenen Browser-Renderer.

Prüfe den RAM-Verbrauch und die Unterstützung moderner Websites.

Der Browser muss unterstützen:

- HTTPS
- Adressleiste
- Vorwärts und Zurück
- Neuladen
- JavaScript
- Downloads
- Tastatur
- Maus
- Vollbild

Der Browser erhält pro Linux-Systembenutzer eigene Datenverzeichnisse.

Verwende möglichst vorhandene Browserinstallationen, wenn diese die Anforderungen erfüllen.

---

# 16. Setup-Assistent und Einstellungen

Erstelle einen vollständig grafischen, überspringbaren Setup-Assistenten.

Er umfasst:

1. Sprache und Tastaturlayout
2. HDMI-Anzeige
3. WLAN
4. Bluetooth
5. Linux-Systembenutzer und Login
6. VPN
7. Windows-Host
8. SSH-Schlüssel
9. Codex
10. Claude Code
11. Antigravity
12. Desktop-Streaming
13. RDP
14. Kanban
15. Abschlussdiagnose

Die grafischen Einstellungen verwenden dieselben vorhandenen Systemdienste und Schnittstellen wie der Assistent.

Entwickle keine zweite unabhängige Konfigurationslogik.

Gemeinsame Funktionen sollen in zentralen, wiederverwendbaren Komponenten organisiert werden.

---

# 17. Installation auf Raspberry Pi und Windows

## Raspberry Pi

Erstelle `setup.sh` für Raspberry Pi OS Lite.

Das Skript muss:

- Hardware erkennen
- Betriebssystem erkennen
- Vorhandene Dienste und Pakete prüfen
- Geeignete Installationen wiederverwenden
- Nur fehlende Abhängigkeiten installieren
- Vorhandene Konfigurationen respektieren
- Rampi installieren
- Systemdienste einrichten
- Grafische Sitzung konfigurieren
- Bootanimation integrieren
- Setup-Assistent bereitstellen
- Installation überprüfen

Das Skript muss möglichst idempotent sein.

Keine unnötigen Änderungen an `/boot` oder der Firmwarekonfiguration.

Erstelle zusätzlich:

- `update.sh`
- `uninstall.sh`
- `diagnostics.sh`
- `repair.sh`

## Windows 11 Pro

Erstelle `setup.ps1`.

Dieses Skript erkennt und verwendet vorhandene:

- OpenSSH-Installationen
- CLI-Programme
- Remote-Desktop-Dienste
- Sunshine-Installationen
- VPN-Software
- Windows-Systemfunktionen

Nur tatsächlich fehlende oder inkompatible Komponenten werden installiert beziehungsweise nach expliziter Freigabe angepasst.

Installiere nicht ungefragt dieselbe Anwendung mehrfach.

Erstelle außerdem:

- `update.ps1`
- `uninstall.ps1`
- `diagnostics.ps1`

Sicherheitskritische Änderungen müssen transparent und autorisiert sein.

---

# 18. GitHub-Repository

Erstelle ein öffentliches GitHub-Repository.

Bevorzugter Name:

`rampi-os`

Verwende Apache License 2.0 für den eigenentwickelten Code.

Erstelle:

- `README.md`
- `LICENSE`
- `NOTICE`, soweit erforderlich
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `.gitignore`
- `.editorconfig`
- Issue-Templates
- Pull-Request-Template
- Dokumentationsverzeichnis
- GitHub-Actions-Workflows

Verwende `main` als Hauptbranch.

Verwende nachvollziehbare Commits und Feature-Branches.

Nutze Conventional Commits.

Erhalte eine saubere Projekt- und Versionshistorie.

---

# 19. Automatisierte CI/CD

Verwende GitHub Actions.

Die Pipelines müssen automatisiert ablaufen.

## Continuous Integration

Bei Pull Requests und geeigneten Commits:

- Build
- Linting
- Typprüfung
- Unit-Tests
- Integrationstests
- Sicherheitsscans
- Secret-Scanning
- Lizenzprüfung
- Prüfung der Installationsskripte
- Prüfung der Release-Konfiguration

Nutze vorhandene etablierte CI-Werkzeuge.

Entwickle kein eigenes allgemeines Build- oder CI-System, wenn bestehende Werkzeuge ausreichen.

## Versionierung

Nutze Semantic Versioning und Conventional Commits.

Die Versionierung erfolgt automatisiert.

Neue releasefähige Änderungen führen entsprechend der definierten Regeln zu einem neuen Versionsstand.

Automatische Git-Tags verwenden das Format:

`vMAJOR.MINOR.PATCH`

## GitHub Releases

Reguläre Releases werden nach erfolgreicher Freigabe automatisch erzeugt und veröffentlicht.

Jeder Release enthält:

- Git-Tag
- Release Notes
- Raspberry-Pi-Systemimage
- `setup.sh`
- Windows-Hostpaket
- `setup.ps1`
- Prüfsummen
- Lizenzinformationen
- Versionsinformationen

Nutze vorhandene etablierte Release-Werkzeuge.

Sichere den Release-Prozess gegen unvollständige Builds und doppelte Veröffentlichungen ab.

Keine automatischen Updates auf den Endgeräten.

---

# 20. Automatisierter Systemimage-Build

Entwickle einen reproduzierbaren Image-Build für den Raspberry Pi 3 Model B+.

Nutze vorhandene offizielle beziehungsweise etablierte Raspberry-Pi-Image-Build-Werkzeuge, sofern kompatibel.

Erstelle kein eigenes allgemeines Image-Build-System, wenn ein vorhandenes die Anforderungen erfüllt.

Das Image enthält:

- Unterstützte Raspberry-Pi-OS-Lite-Basis
- Rampi-Oberfläche
- Notwendige Dienste und Programme
- Alle implementierten Module
- Bootanimation
- Login-Integration
- Setup-Assistent
- Grafische Systemeinstellungen
- Benötigte grafische Assets

Keine persönlichen Zugangsdaten oder fest eingebauten Passwörter.

Das Image wird bei jedem regulären Release automatisch erzeugt.

Beispiel:

`rampi-os-rpi3bplus-vX.Y.Z.img.xz`

Prüfe automatisch:

- Architektur
- Dateisystem
- Partitionen
- Bootdateien
- Systemdienste
- Pakete
- Versionskonsistenz
- Dateiberechtigungen
- Vorhandensein der Rampi-Komponenten

Echte Hardwarekompatibilität muss anhand realer Tests validiert werden; Build-Erfolg allein gilt nicht als Hardwaretest.

---

# 21. Sicherheit und Lizenzkonformität

Verwende bewährte Sicherheitsmechanismen.

Insbesondere:

- PAM
- SSH-Schlüssel
- Etablierte VPN-Software
- Sichere Secret-Speicher
- Benutzerrechte
- Geschützte Konfigurationsdateien
- Minimale Prozessprivilegien
- Sichere Prozessstarts
- Keine unnötigen offenen Ports
- Verifizierte Abhängigkeiten
- Geschützte CI/CD-Secrets

Entwickle keine eigene Kryptografie.

Überprüfe die Lizenzbedingungen verwendeter Programme, Bibliotheken, Schriftarten und Bilder.

Der eigenentwickelte Rampi-Code steht unter Apache License 2.0.

Drittanbieterkomponenten behalten ihre jeweiligen Lizenzbedingungen.

KI-CLI-Anwendungen müssen nicht zwingend im Rampi-Repository oder im Systemimage mitgeliefert werden, wenn dies lizenzrechtlich oder technisch nicht zulässig ist.

Verwende in solchen Fällen die offiziellen Installationswege.

---

# 22. Dokumentation

Erstelle umfassende technische Dokumentation.

Mindestens:

- `README.md`
- `ARCHITECTURE.md`
- `DESIGN-SYSTEM.md`
- `INSTALL-RASPBERRYPI.md`
- `INSTALL-WINDOWS11.md`
- `EXISTING-SERVICES.md`
- `CONFIGURATION.md`
- `AI-TERMINALS.md`
- `REMOTE-DESKTOP.md`
- `NETWORK.md`
- `VPN.md`
- `SECURITY.md`
- `PERFORMANCE.md`
- `CI-CD.md`
- `IMAGE-BUILD.md`
- `RELEASING.md`
- `TROUBLESHOOTING.md`
- `TESTING.md`
- `LICENSES.md`

In `EXISTING-SERVICES.md` ist besonders ausführlich zu dokumentieren:

- Welcher vorhandene Dienst verwendet wird
- Warum er ausgewählt wurde
- Welche Versionen unterstützt werden
- Wie seine Installation erkannt wird
- Welche Konfiguration Rampi übernimmt
- Welche Schnittstelle verwendet wird
- Welche Berechtigungen notwendig sind
- Welche Komponenten Rampi selbst implementiert
- Warum eventuell eine vorhandene Alternative nicht geeignet ist

Dokumentiere alle öffentlichen Einstellungen einschließlich Zweck, Datentyp, Standardwerten und Auswirkungen.

---

# 23. Qualitätssicherung und Performance

Teste:

- Systemstart
- Benutzeranmeldung
- Tastaturnavigation
- Mauszeigerausblendung
- Animationen
- WLAN
- Bluetooth
- VPN
- Terminalintegration
- Persistente Windows-Sitzungen
- Remote Desktop
- Kanban
- Browser
- Installationsskripte
- Benutzerisolation
- CI/CD
- Image-Build
- Release-Erstellung

Miss außerdem:

- RAM-Verbrauch
- CPU-Auslastung
- Startgeschwindigkeit
- Animationsleistung
- Eingabelatenz
- Remote-Desktop-Latenz
- Modulwechselzeiten

Prüfe insbesondere, ob vorhandene Dienste durch die Rampi-Integration unnötig mehrfach gestartet werden.

Optimiere die tatsächliche Ressourcenverwendung.

Tests auf echter Raspberry-Pi-Hardware und Windows 11 Pro sind von simulierten beziehungsweise automatisierten Umgebungsprüfungen klar zu unterscheiden.

---

# 24. Projektstruktur

Verwende eine übersichtliche Monorepo-Struktur.

Beispiel:

- `.github/workflows/`
- `assets/references/`
- `assets/branding/`
- `assets/icons/`
- `client/`
- `host/windows/`
- `modules/`
- `integrations/`
- `system/`
- `installer/raspberrypi/`
- `installer/windows/`
- `image/`
- `packaging/`
- `scripts/`
- `tests/`
- `docs/`

Innerhalb von `integrations/` werden die Adapter für vorhandene Dienste und Programme organisiert.

Doppelte Implementierungen sollen vermieden werden.

Gemeinsame Funktionen erhalten geeignete zentrale Komponenten.

---

# 25. Verbindlicher Entwicklungsablauf

Arbeite in dieser Reihenfolge:

**Phase 1: Bestandsaufnahme**

Analysiere die Zielhardware, vorhandene Dienste, bestehende Programme und beigefügte Referenzbilder.

**Phase 2: Wiederverwendungsanalyse**

Erstelle eine technische Matrix aller benötigten Funktionen und der dafür vorhandenen geeigneten Lösungen.

Dokumentiere, welche Komponenten übernommen werden und welche Rampi-spezifischen Implementierungen erforderlich sind.

**Phase 3: Architektur**

Definiere den vollständigen Tech-Stack und die minimal notwendige Eigenentwicklung.

**Phase 4: GitHub**

Initialisiere das Git-Repository und erstelle das öffentliche GitHub-Projekt mit Apache-2.0-Lizenz.

**Phase 5: Design**

Setze die beiden Referenzbilder in ein konsistentes Rampi-Designsystem um.

**Phase 6: Raspberry-Pi-Client**

Implementiere die eigenständige grafische Rampi-Oberfläche.

**Phase 7: Windows-Host**

Integriere OpenSSH, die nativen KI-CLIs, die Sitzungsverwaltung und Remote-Desktop-Dienste.

**Phase 8: Systemintegrationen**

Integriere NetworkManager, BlueZ, Tailscale, WireGuard, PAM, systemd und weitere erforderliche bestehende Komponenten.

**Phase 9: Hauptmodule**

Implementiere die sechs funktionsfähigen Rampi-Module.

**Phase 10: Installation**

Erstelle und teste die Raspberry-Pi- und Windows-Installationsskripte.

**Phase 11: CI/CD**

Implementiere automatisierte Prüf-, Build-, Tag- und Release-Pipelines.

**Phase 12: Systemimage**

Implementiere den reproduzierbaren automatisierten Image-Build.

**Phase 13: Tests und Performance**

Führe alle verfügbaren Tests durch, behebe Fehler und optimiere die Performance.

**Phase 14: Veröffentlichung**

Veröffentliche den ersten vollständig geprüften releasefähigen Stand über GitHub Actions.

---

# 26. Abschließende Entwicklungsregeln

Für Rampi gelten folgende verbindliche Grundsätze:

1. **Vorhandene Lösungen verwenden, bevor eigene entwickelt werden.**
2. Vorhandene Installationen und Dienste zuerst erkennen und prüfen.
3. Keine unnötigen Neuinstallationen oder konkurrierenden Prozesse.
4. Keine Eigenentwicklung etablierter Netzwerk-, Sicherheits- oder Grafikprotokolle.
5. Eigene Entwicklung auf Benutzeroberfläche und notwendige Integrationen konzentrieren.
6. Raspberry-Pi-3-B+-Performance konsequent berücksichtigen.
7. Vollständige Linux-Systembenutzerisolation gewährleisten.
8. Windows-11-CLIs nativ ausführen.
9. Persistente Windows-KI-Sitzungen tatsächlich gewährleisten.
10. Alle sechs Hauptmodule funktionsfähig implementieren.
11. Beigefügte Designs und Logos tatsächlich verwenden.
12. Automatisierte GitHub-Pipelines, Tags und Releases erstellen.
13. Bei regulären Releases ein flashbares Systemimage veröffentlichen.
14. `setup.sh` und `setup.ps1` als Release-Artefakte bereitstellen.
15. Updates auf installierten Systemen ausschließlich manuell durchführen.
16. Apache License 2.0 und Drittanbieterrechte einhalten.
17. Keine simulierten Funktionen als fertig ausgeben.
18. Keine nicht durchgeführten Tests als erfolgreich ausgeben.
19. Verständliche, vollständige Dokumentation bereitstellen.
20. Ein langfristig wartbares, professionelles Open-Source-Projekt entwickeln.

## Finale Anweisung

Beginne mit einer vollständigen Prüfung der vorhandenen Programme, Dienste, Systemfunktionen und Bibliotheken.

Wähle für jede Funktion die geeignetste etablierte Lösung.

Entwickle ausschließlich die für Rampi tatsächlich notwendigen eigenen Komponenten.

Nutze die beiden beigefügten Bilder als verbindliche Design- und Logo-Grundlagen.

Erstelle anschließend den vollständigen Rampi-Quellcode, das GitHub-Repository, die Installer, die Systemimage-Build-Pipeline und den automatisierten Release-Prozess.

**Das Ziel ist kein von Grund auf neu erfundenes Betriebssystem, sondern eine eigenständige, perfekt integrierte, hochwertige und extrem ressourcenschonende Remote-Arbeitsumgebung auf Basis bewährter Systemkomponenten.**

**Beginne jetzt mit der technischen Bestandsaufnahme und anschließend der tatsächlichen Implementierung von Rampi OS.**