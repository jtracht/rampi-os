# Testnachweise und Abnahme

19./20.10.2026 tatsächlich ausgeführt:

- Native Qt-Quick-Anwendung gestartet und Screenshot erzeugt.
- 27 Python-Tests auf Windows und im ARM64-Trixie-Container erfolgreich: Konfiguration, private Rechte auf geeigneten
  Systemen, sichere Argumente, Zertifikatsoptionen, lokale Boards/Cache,
  Credential-Cachetrennung, GitHub-Paginierung mit Fixtures, Redirect-Schutz.
- Ruff und mypy für den Client erfolgreich.
- PowerShell-Skripte mit dem nativen Parser geprüft; Diagnose tatsächlich ausgeführt.
- psmux 3.4.0 anhand des offiziellen Release-Digests geprüft; ein nativer
  ConPTY-Prozess produzierte nach Ende unabhängiger Clients weitere Ausgaben.
- Tatsächlicher ARM64-Containerlauf unter 1 GB RAM und vier CPUs: libnm-Import
  mit persönlichen Profilrechten sowie QML-Navigation erfolgreich.
- Echte AccountsService-/PAM-Prüfung im wegwerfbaren ARM64-Container: normales
  Konto angelegt; richtiges Passwort akzeptiert und falsches abgewiesen.

Physische Hardwaretests sind auf ausdrücklichen Nutzerwunsch ausgeschlossen.
Siehe [VALIDATION-SCOPE.md](VALIDATION-SCOPE.md). Weitere verbindliche Nachweise
sind die jeweils abgeschlossenen CI-Jobs und Imagevalidierung, keine Schätzungen.

Das sind keine erfolgreichen Live-Tests gegen Cloud-Kanban-Konten und kein
SSH-/VPN-Unterbrechungs- oder Mehrbenutzertest. Aktuelle CI-Ergebnisse und neu
hinzugefügte Tests haben Vorrang vor dieser anfänglichen Momentaufnahme.

Ursprünglicher Hardware-Messplan, jetzt ausdrücklich ausgenommen: Pi-3-B+-Boot/Login; Bluetooth-Tastatur ab Erststart; WLAN-Passwort;
Tailscale-Authentifizierung; WireGuard-Profilrechte/Routing; Linux-/Windows-Kontotrennung;
SSH-Abbruch/Reattach während laufender CLI; alle offiziellen CLI-Anmeldungen;
RDP-Zertifikat/Shortcuts; Sunshine/Moonlight-Decodierung/Audio; Browserdownloads;
Image-Partitionen, Flash und Boot; Deinstallation/Rollback; Performancewerte.

`scripts/test-persistence.ps1` nutzt einen zufälligen psmux-Namespace und beendet
nur diesen Testserver. Keine bestehenden persönlichen Sitzungen werden beendet.
`python -m rampi.app --smoke-test` lädt die tatsächliche QML-Oberfläche, keine
HTML-Nachbildung. `--screenshot DATEI` speichert das gerenderte native Fenster.
