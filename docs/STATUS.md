> **Architekturwechsel am 21.10.2026:** Die Anwendung wird auf Rust/GTK 4/Wayland
> portiert. Aktueller Gesamtstand nach neuem Maßstab: ca. 50 %; Rust-Port ca. 42 %.
> Die nachfolgenden Angaben zum Python-/QML-Prototyp sind historische Nachweise.
> Aktueller Umfang und offene Arbeiten: [Rust-Migration](RUST-MIGRATION.md).

# Implementierungs- und Abnahmestand

Stand: 20. Oktober 2026. Physische Hardwaretests sind auf Nutzerwunsch durch
[Softwareabnahme](VALIDATION-SCOPE.md) ersetzt.

| Bereich | Implementierung und tatsächlich geprüfter Umfang |
|---|---|
| Dashboard | Native Qt-Quick-Oberfläche, sechs Kacheln, Original-Logo, Lucide-Icons, 200-ms-Verformung aller Kanten; unter Linux/Windows geprüft |
| Eingabe | Pfeile, Enter, Escape, Tab, Cursorwechsel; tatsächlicher QML-Test und globales Openbox-Kürzel unter virtuellem X11 |
| Einrichtung | 15-Themen-Assistent, grafische Verwaltung mehrerer Hostprofile mit Projektverzeichnis und expliziter Aktivierung, SSH-Fingerprint-Vergleich und Secret-Service-Tokenablage |
| Benutzer | LightDM/PAM und Linux-Systemkonten; AccountsService-Kontoanlage und korrektes/falsches Passwort im ARM64-Container geprüft |
| Netzwerk/VPN | Eigene WLAN-Auswahl und Kennworteingabe über NetworkManager-D-Bus, asynchroner Scan/Verbindungsaufbau, bestehende BlueZ-Dialoge; echter libnm-Import mit persönlichen Rechten; grafische persönliche WireGuard-Profilauswahl mit aktivem Zustand; Tailscale/WireGuard über vorhandene Dienste |
| KI-Terminals | Offizielle native codex/claude/agy, VTE/OpenSSH und bestehendes psmux/ConPTY; Windows-Prozess nach abruptem SSH-Abbruch wieder erreichbar, zwei Konten getrennt; grafischer Status, Wiederverbindung und bestätigtes Beenden pro Anbieter |
| Kanban | Lesende JSON-, GitHub-, Trello-, Jira-, Asana-/Notion-Adapter, Details, kombinierte Suche und Projekt-/Prioritäts-/Statusfilter, grafische Spaltenreihenfolge und privater Offline-Cache; Vertragstests, keine persönlichen Cloudkonten |
| Remote Desktop | FreeRDP mit interaktiver Anmeldung und TOFU; Sunshine/Moonlight Embedded 2.7.1 mit persönlichen Kopplungsschlüsseln je Host/Windows-Konto und SDL/FFmpeg im vorhandenen X11; Sunshine teilt die aktive Konsole, keine Windows-Kontenisolierung durch Pairing |
| Browser | Vorhandenes Chromium/Firefox, eigenes Benutzerprofil, Start bei Bedarf |
| Installation | Linux-/Windows-Bestandsaufnahme, sichere Adapter-ACL, Datenbewahrung, manuelle Updates; echte Windows-Installer-Prüfung in CI |
| Image | Festgelegter offizieller pi-gen-Commit, Lite Trixie arm64, Plymouth, LightDM, Paketmanifest/Lizenzarchiv; erzeugt, virtuelle Abnahme siehe Actions |
| CI/Release | ARM64-Docker mit 1-GB-Limit, Linux/Windows, Sicherheits-/Skript-/Archivprüfungen; Veröffentlichung erfordert Softwarebelege und frisch bestandenen Imageworkflow |

87 Python-Tests prüfen Konfiguration, Argumente, Cachetrennung, Anbieter-Verträge,
Hostschlüsselrotation und Zugangsdatenübergabe ohne Token in Prozessargumenten.
Zusätzliche Integrationstests verwenden echte Systemkomponenten; die WLAN-Oberfläche hat einen ausdrücklich gekennzeichneten D-Bus-Fixture-Test und einen separaten echten NetworkManager-Profil-/Secret-Test ohne Funkgerät. [WLAN-Bedienung und Testgrenzen](WIFI.md). Komplexe
Netzwerkeinstellungen und Bluetooth-Pairing verwenden gepflegte Systemdialoge.

FreeRDP hat gegen einen isolierten echten xrdp/PAM-Server TLS-Anmeldung,
Bildübertragung, Tastatureingaben, Wiederverbindung und Zertifikatsablehnung
bestanden. Sunshine und Moonlight haben unter Linux mit Software-Videocodierung
die tatsächliche PIN-Kopplung, Ablehnung eines nicht gekoppelten Profils und
wechselnde übertragene Videobilder bei zwei Verbindungen bestanden. Zusätzlich
kommt ein echter serverseitiger Testton nach Opus-/SDL-Decodierung korrekt an;
Stille und eine andere Frequenz werden als unzureichender Nachweis abgewiesen.
Persönliche Cloudanmeldungen, Tailscale-Netze, Windows-RDP/NLA und Windows-
Sunshine sind noch ungeprüft. Streaming-Eingabe und physische
Funk-/HDMI-/GPU-/Latenzwerte werden durch diese Tests nicht nachgewiesen.
Images sind durch Quellenrevision und Paketmanifest nachvollziehbar, wegen
beweglicher Paketspiegel bislang nicht bitweise reproduzierbar.
[Testnachweise](TESTING.md); aktuelle Freigabe in packaging/readiness.json.
[Streaming und Windows-Kontengrenzen](STREAMING.md).
[Gesamtfortschritt: ca. 75 % mit Bewertungsmaßstab](PROGRESS.md).
