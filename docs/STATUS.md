# Implementierungs- und Abnahmestand

Stand: 19. Oktober 2026. Kein regulärer Release freigegeben.

| Bereich | Implementiert | Nachweis / offene Arbeit |
|---|---|---|
| Qt-Quick-Dashboard | Sechs Kacheln, farbige Panels, Original-Logo, 200-ms-Verformung aller Kanten | Windows-Start und Screenshot; Pi-GPU und Bildrate offen |
| Eingabe | Qt-Fokus, Pfeile, Tab, Enter, Escape, Cursorwechsel | Automatisierter QML-Test und Hardwarebedienung ergänzen |
| Einstellungen | Gemeinsames Backend, Host-/Browser-/Kanban-Profil, Systemdialoge | Noch kein vollständiger grafischer Assistent mit 15 Schritten |
| Benutzer | Ausschließlich Linux-/Windows-Konten, persönliche Dateien | PAM über LightDM; Mehrbenutzer-Endtest offen |
| WLAN | Async-Status, Scan, NetworkManager-Systemdialog | Keine eigene Passwortspeicherung; Pi-Test offen |
| Bluetooth | BlueZ-Status, Blueman-Pairingdialog | Native Integration, noch keine eigene vollständige Pairingoberfläche |
| Tailscale | Status, verbinden, trennen | Bereits installierter Dienst erforderlich; Endtest offen |
| WireGuard | NM-Import, Profile, verbinden, trennen | Benutzerberechtigungen des Imports müssen vor Aktivierung geprüft werden |
| KI | Offizielle codex/claude/agy, OpenSSH, psmux-Adapter | Lokaler nativer Prozesspersistenztest bestanden; SSH-Abbruch offen |
| Kanban JSON | Lesen, Spalten, Titel, Beschreibung, Priorität, Suche, Cache | Unit-Tests bestanden |
| Cloud-Kanban | GitHub Projects, Trello, Jira, Asana, Notion lesende Adapter | Fixtures testen GitHub-Paginierung; Live-Konten fehlen, noch nicht als unterstützt freigegeben |
| RDP | FreeRDP-Aufruf, interaktive Authentifizierung, TOFU-Zertifikate | Endtest und Shortcut-Weiterleitung auf Pi offen |
| Streaming | Moonlight-Embedded-Aufruf | Installation/Decodierung/VT-Nutzung unter Trixie auf Pi 3 ungeprüft |
| Browser | Bestehendes Chromium/Firefox mit persönlichem Profil | Kein eigener Renderer; RAM- und Downloadtest auf Pi offen |
| Installer | Audit/Install, Windows-Opt-ins, manuelle Updates, vorsichtige Deinstallation | PowerShell-Audit lokal; Linux-Installation noch nicht auf Pi geprüft |
| Image | Festgelegter pi-gen-Commit, eigene Stage, Rootfs-Prüfungen | Kein Flash-/Boottest belegt; nicht bitweise reproduzierbar, Paketquellen noch nicht eingefroren |
| Bootanimation | Plymouth als Architekturentscheidung | Noch nicht integriert |
| CI/Release | Workflows, Artefakte, Prüfsummen, Release-Sperre | Aktuelle Actions-Ergebnisse im Repository prüfen |

Die offenen Punkte sind echte Entwicklungsarbeit und keine vom Dashboard
simulierten Erfolgsmeldungen. `packaging/readiness.json` sperrt reguläre Releases,
solange die geforderten Nachweise fehlen.
