# Wiederverwendungsanalyse und Bestandsaufnahme

Entwicklungsrechner: Windows 11 Pro, Build 26300, x64; Git 2.55.0, Python 3.12.10,
Node 24.16.0, GitHub CLI mit Konto `jtracht`, Docker Engine 29.8.2 vorhanden.
OpenSSH-Server vorhanden, zum Prüfzeitpunkt gestoppt. TermService lief.
Codex und Claude im Benutzerpfad vorhanden. agy, psmux, Sunshine und VPN-Werkzeuge
wurden nicht im normalen PATH gefunden. Für den Test wurde psmux 3.4.0 ausschließlich
unter `.tools/` entpackt und mit dem offiziellen Release-SHA256 geprüft.
Der Host-Installer wurde zunächst ausschließlich im Auditmodus ausgeführt.
Ein Raspberry Pi ist dieser Entwicklungsumgebung bisher nicht zugänglich.

| Funktion | Übernommene Lösung / Version | Erkennung | Schnittstelle / Rechte | Rampi-Anteil |
|---|---|---|---|---|
| Grafik | Debian Qt 6.8.2.1/PySide6, Entwicklung 6.8.3 | Paketdatenbank, Import | Qt Quick, Benutzer | Design, Pfade, Fokus, Dashboard |
| Sitzung | Xorg, Openbox, LightDM aus Trixie | dpkg, systemctl | Xsession, PAM; Installation root | Sitzungsdatei und Tastenkürzel |
| Dienste | systemd aus Trixie | systemctl | Benutzerdienst | eng begrenzte Unit, Restart-on-failure |
| Authentifizierung | PAM/Linux-Konten | LightDM/PAM-Konfiguration | bestehende Systemrechte | Keine Passwortdatenbank |
| WLAN | NetworkManager aus Trixie | nmcli, dpkg | nmcli/nm-connection-editor über NM-D-Bus, polkit | Async-Scan und Status |
| Bluetooth | BlueZ/Blueman aus Trixie | bluetoothctl, dpkg | vorhandene Agent-/D-Bus-Integration, polkit | Status und Dialogstart |
| Tailscale | vorhandene offizielle Installation | PATH, status --json | offizielle CLI; Daemon-Berechtigungen | Status/Up/Down |
| WireGuard | Kernel/WireGuard-tools/NM aus Trixie | wg, NM-Profile | NM-Import, UUID-Operationen, polkit | Profilwahl und Diagnose |
| Linux-Terminal | xfce4-terminal/VTE aus Trixie | PATH | lokaler Benutzerprozess | einmaliger bedarfsweiser Start |
| Windows-Terminal | psmux 3.4.0 (MIT) | Get-Command, --version | ConPTY, persönliche Serverinstanz | feste Anbieter-Allowlist |
| SSH | offizielles OpenSSH | Get-Command/Get-Service | SSH-Keys, bekannte Hostschlüssel | geprüfte Argumente, Keepalive |
| RDP | Microsoft RDP/FreeRDP 3 aus Trixie | TermService/xfreerdp3 | interaktive Credentials, Zertifikatsprüfung | persönlicher Host-Aufruf |
| Streaming | Sunshine/Moonlight Embedded 2.7.1 als Kandidat | Get-Command/moonlight | existierendes Protokoll, Pairing | noch zu validierender Aufruf |
| Browser | vorhandenes Chromium, sonst Firefox | PATH | eigenes Profil im Benutzerverzeichnis | bedarfsgerechter Start |
| Secrets | GNOME Keyring/Secret Service | secret-tool | freigeschalteter persönlicher Keyring | Profilname statt Token in JSON |
| CI | GitHub Actions | Repository-Workflows | minimale Job-Berechtigungen | projektspezifische Checks |
| Releases | Release Please v4 | Workflow-Konfiguration | zunächst Drafts | Hardware-/Artefaktfreigabe |
| Images | offizielles pi-gen, Commit in image/pi-gen-revision | Git-Commit | bestehende Image-Pipeline | einzelne zusätzliche Stage |
| Bootscreen | Plymouth geprüft als bevorzugte Lösung | künftig dpkg/theme-Prüfung | vorhandenes Bootsystem | noch nicht implementiert |

Debian-Paketversionen werden in jedem Image als Manifest erfasst. Dies ist keine
pauschale Unterstützung aller älteren Versionen. Das Installerziel ist bewusst
Trixie arm64. Andere Systeme werden ohne stillen Fallback abgelehnt.

NetworkManager/BlueZ werden derzeit über ihre vorhandenen CLI-/GUI-Adapter
verwendet. Eigene direkte D-Bus-Formulare sind noch ausstehend. Das vermeidet
eine zweite Passwort-/Pairingimplementierung, erfüllt aber noch nicht den
vollständigen eigenen grafischen Einstellungsumfang des Masterauftrags.

SSH allein bewahrt keine laufenden interaktiven Prozesse. Windows Terminal ist
ein Frontend, kein verlässlicher SSH-Multiplexer. psmux bietet dagegen bereits
den erforderlichen abgekoppelten ConPTY-Server; ein eigener Broker wäre unnötig.
WSL und ein eigener Browserrenderer wurden deshalb nicht eingeführt.
