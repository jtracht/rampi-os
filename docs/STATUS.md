# Implementierungs- und Abnahmestand

Stand: 20. Oktober 2026. Die ursprüngliche Hardwareabnahme ist durch die
Softwareabnahme aus [VALIDATION-SCOPE.md](VALIDATION-SCOPE.md) ersetzt.

| Bereich | Implementiert | Nachweis / offene Arbeit |
|---|---|---|
| Qt-Quick-Dashboard | Sechs Kacheln, farbige Panels, Original-Logo, 200-ms-Verformung aller Kanten | Windows-Start und Screenshot; Pi-GPU und Bildrate offen |
| Eingabe | Qt-Fokus, Pfeile, Tab, Enter, Escape, Cursorwechsel | Nativer QML-Test für sechs Fokuswechsel, Enter und Escape erfolgreich |
| Einstellungen | Gemeinsames Backend, Host-/Browser-/Kanban-Profil, 15-Themen-Assistent | Vorhandene Systemdialoge werden wiederverwendet |
| Benutzer | Ausschließlich Linux-/Windows-Konten, persönliche Dateien | PAM über LightDM; Mehrbenutzer-Endtest offen |
| WLAN | Async-Status, Scan, NetworkManager-Systemdialog | Keine eigene Passwortspeicherung; Pi-Test offen |
| Bluetooth | BlueZ-Status, Blueman-Pairingdialog | Native Integration, noch keine eigene vollständige Pairingoberfläche |
| Tailscale | Status, verbinden, trennen | Bereits installierter Dienst erforderlich; Endtest offen |
| WireGuard | libnm-Import, persönliche ACL vor Speicherung, Autostart aus | Echter libnm-Test im Trixie-Container erfolgreich |
| KI | Offizielle codex/claude/agy, OpenSSH, psmux-Adapter | Lokaler nativer Prozesspersistenztest bestanden; SSH-Abbruch offen |
| Kanban JSON | Lesen, Spalten, Titel, Beschreibung, Priorität, Suche, Cache | Unit-Tests bestanden |
| Cloud-Kanban | GitHub Projects, Trello, Jira, Asana, Notion lesende Adapter | Fixtures testen GitHub-Paginierung; Live-Konten fehlen, noch nicht als unterstützt freigegeben |
| RDP | FreeRDP-Aufruf, interaktive Authentifizierung, TOFU-Zertifikate | Endtest und Shortcut-Weiterleitung auf Pi offen |
| Streaming | Gepinntes Moonlight Embedded 2.7.1, SDL/FFmpeg/V4L2 im vorhandenen X11, Pairing | Keine Firmwareänderung; echte GPU-/Funkmessungen aus Testumfang ausgeschlossen |
| Browser | Bestehendes Chromium/Firefox mit persönlichem Profil | Kein eigener Renderer; RAM- und Downloadtest auf Pi offen |
| Installer | Audit/Install, Windows-Opt-ins, manuelle Updates, vorsichtige Deinstallation | PowerShell-Audit lokal; Linux-Installation noch nicht auf Pi geprüft |
| Image | Festgelegter pi-gen-Commit, eigene Stage, Rootfs-Prüfungen | Kein Flash-/Boottest belegt; nicht bitweise reproduzierbar, Paketquellen noch nicht eingefroren |
| Bootanimation | Plymouth-Script-Theme mit Original-Logo, Bildintegration | Kein eigenes Bootsystem |
| CI/Release | Workflows, Artefakte, Prüfsummen, Release-Sperre | Aktuelle Actions-Ergebnisse im Repository prüfen |

Physische Pi-Prüfungen in der Tabelle sind als ausgeschlossen zu lesen; sie
werden nicht nachträglich behauptet. `packaging/readiness.json` fordert jetzt
ausschließlich Software-Nachweise. Noch nicht abgeschlossene CI-Läufe bleiben
offen. Cloudzugänge sind implementiert, aber ohne persönliche Konten nicht live validiert.
