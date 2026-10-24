# Native KI-Terminals

Rampi überträgt ein interaktives OpenSSH-Terminal; VTE rendert die Anzeige.
Der Host startet `codex`, `claude` beziehungsweise `agy` in psmux 3.4.0.
WSL wird nicht benötigt. Anbieteranmeldung, Projektsicherheit und
Berechtigungsdialoge bleiben unverändert in den offiziellen CLIs.
Der gestartete Prozess erhält die offiziellen Abschalter
`DISABLE_AUTOUPDATER=1` (Claude) und `AGY_CLI_DISABLE_AUTO_UPDATE=true`
(Antigravity). So aktualisieren diese Sitzungen sich nicht im Hintergrund.
Die übrige Windows-Umgebung und vorhandene Benutzerprofile werden nicht verändert;
Updates bleiben bewusste manuelle Aktionen. Bereits laufende Sitzungen müssen
bewusst beendet und neu gestartet werden, um die geänderte Startumgebung zu übernehmen.
Quellen: [Claude](https://code.claude.com/docs/en/env-vars),
[Antigravity](https://antigravity.google/docs/cli/troubleshooting/).

Die Kachel öffnet eine eigene Modulseite: **Host und Sitzung prüfen** fragt über
OpenSSH den persönlichen Windows-Adapter ab. Sie unterscheidet vorhandenes
CLI-Programm, psmux und eine tatsächlich laufende benannte Sitzung. Eine vorhandene
Installation bestätigt keine Anbieteranmeldung; Rampi liest keine Authentifizierungsdateien.
Die Hintergrundprüfung kann weder Kennwort- noch Hostschlüssel-Prompts öffnen.
Fehlerhafte Antworten und SSH-Fehler bleiben Fehler, kein positiver Verbindungsstatus.

**Offizielle Einrichtung anzeigen** öffnet die Anbieter-Dokumentation im
eingebetteten Browser. **Sitzung öffnen / wiederverbinden** verwendet VTE und den
vorhandenen ConPTY-Server. **Windows-Sitzung beenden …** verlangt eine eigene
Bestätigungsseite und beendet ausschließlich die exakte Sitzung des angezeigten
Windows-Kontos. Terminals werden zusätzlich nach Host und Konto getrennt, damit
ein Profilwechsel nicht versehentlich das Terminal eines anderen Hosts zeigt.
Die drei Anbieterstationen des Assistenten führen direkt zu diesen Modulseiten;
Zurück führt zum aktuellen Einrichtungsschritt. Bestehende Hostinstallationen
benötigen den aktualisierten persönlichen Adapter für die neue `Check`-Aktion.

Feste Windows-Sitzungen heißen rampi-codex, rampi-claude und rampi-antigravity.
`new-session -A` verbindet erneut mit einer bestehenden Sitzung. Ein SSH-Ausfall
beendet nur den Client, nicht den abgekoppelten ConPTY-Server. Der Windows-CI-Test
hat eine echte OpenSSH-Verbindung während eines laufenden Prozesses abrupt beendet,
danach erneut verbunden und fortlaufende Ausgaben geprüft. Ein zweites Windows-Konto
konnte die fremde Sitzung nicht öffnen. Ein VPN-Transport ist für diesen
Sitzungsmechanismus nicht erforderlich. Bei Rückkehr erneut die Kachel öffnen.
Sitzungen gezielt beenden: Host-Adapter mit `-Module codex -Action Stop` aufrufen.
Den Server nicht pauschal mit kill-server beenden: Er könnte andere persönliche
Sitzungen verwalten. Ein Hostneustart muss Prozesse nicht erhalten.

Für ein anderes Projekt die vorhandene Anbietersitzung bewusst beenden und danach
mit neuem Projektprofil öffnen. Anbieterfunktionen zur Wiederaufnahme werden
innerhalb der offiziellen CLI verwendet; Rampi erfindet keine Resume-Flags.

Quellen (19.10.2026):
- https://github.com/openai/codex
- https://code.claude.com/docs/en/setup
- https://www.antigravity.google/docs/cli/install/ (`agy`, native Windows-Unterstützung)
- https://github.com/psmux/psmux (ConPTY, SSH, serverseitige Persistenz, MIT)
