# Testnachweise und Abnahme

Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen. Verbindlicher
Ersatzumfang: [VALIDATION-SCOPE.md](VALIDATION-SCOPE.md).

Die aktuelle Suite enthält 74 Python-Tests. Für die eigene WLAN-Oberfläche
prüft `scripts/test-wifi-ui.py` echte QML-Tastatureingabe und GIO-D-Bus-Aufrufe
gegen das isolierte NetworkManager-Template von python-dbusmock: maskiertes
Kennwort, private Profilübergabe, keine Zugangsdaten in Meldungen/Dateien,
Profilwiederverwendung, Trennen und Scan. Diese Aktivierung ist eine Fixture,
kein Nachweis einer Funkanmeldung oder von DHCP über WLAN.

Zusätzlich prüft `scripts/test-wifi-profile.py` im echten NetworkManager der
Wegwerf-VPN-Container die Speicherung eines privaten WLAN-Profils, unveränderte
Benutzer-ACL, ausgeblendetes Geheimnis in Metadaten und verweigerten
Geheimnisabruf durch ein anderes Linux-Konto. libnm validiert offene, WPA2-
und SAE-Profile und lehnt ein zu kurzes WPA2-Kennwort ab. Dabei wird kein WLAN
aktiviert. Bedienung, Quellen und weitere Grenzen: [WIFI.md](WIFI.md).

Am 19./20.10.2026 tatsächlich ausgeführt:

- 36 Python-Tests auf Windows, Linux und nativem ARM64-Trixie: private
  Konfiguration, sichere Argumente, Zertifikatsoptionen, Anbieter-Verträge,
  Cachetrennung, Redirect-Schutz, Hostschlüsselrotation und Secret-Übergabe.
- Tatsächliches QML geladen, sechs Fokuswechsel, Enter und Escape geprüft;
  gerenderter Screenshot, kein HTML-Ersatz.
- ARM64-Docker unter 1 GB RAM und vier CPUs: echte libnm-Importvalidierung,
  Benutzer-ACL vor Speicherung, Autostart deaktiviert.
- AccountsService/PAM im wegwerfbaren ARM64-Container: normales Konto angelegt,
  richtiges Passwort akzeptiert, falsches abgewiesen.
- Tatsächlicher GNOME-Keyring-/Secret-Service-Rundlauf in isoliertem D-Bus:
  Token gespeichert und gelesen, verschlüsselte Datei und persönliche Rechte
  bestätigt (CI 39338203802).
- Virtuelles X11 mit Openbox/Qt: Ctrl+Alt+Home wechselt vom zweiten Fenster
  zum Dashboard. Der Home-Tastendruck erreicht das andere Fenster nicht.
  X11 kann nach Ende des Grabs ein alleinstehendes KeyRelease liefern;
  dieses löst keine Home-Aktion aus.
- Offizielles psmux 3.4.0 per SHA256 geprüft, native Prozesspersistenz lokal
  unter Windows 11 Pro und in Windows-CI bestätigt.
- Windows-CI: isolierter OpenSSH-Server, zwei temporäre normale Konten,
  echten interaktiven SSH-Client abrupt beendet, erneut verbunden und
  fortlaufende Ausgabe bestätigt; fremdes Konto kann Sitzung nicht öffnen.
- Windows-Installer in CI ausgeführt: unsichere Alt-ACL ersetzt, nur Benutzer
  und SYSTEM zugelassen; persönliche Daten erhalten.
- Ruff, mypy, ShellCheck, PowerShell-Analyse, pip-audit, Secret-Scan,
  Lizenzdokumente, vollständige Quell-/Windows-Archive und Prüfsummen.

Windows-Integrationstests laufen auf GitHub-Windows-Runnern, nicht auf einem
virtuellen Windows-11-Pro-Desktop. Lokale Persistenz und Bestandsaufnahme liefen
auf dem vorhandenen Windows 11 Pro. CI verändert keine persönlichen Konten
oder bestehenden Hostdienste.

Imageworkflow: offizieller pi-gen-Build, readonly FAT-/ext4-Prüfungen,
Partitionslayout, Bootdateien, Paketmanifest und Lizenzarchiv. QEMU muss den
echten systemd-Healthcheck RAMPI_BOOT_OK erreichen; ein Build allein ist kein
Bootnachweis. Aktuelle Ergebnisse: [GitHub Actions](https://github.com/jtracht/rampi-os/actions).
Fehlgeschlagene Prüfungen werden vor Freigabe behoben, nicht als bestanden gewertet.
Die [Softwareabnahme vom 20.10.2026](validation/software-acceptance-2026-10-20.md)
verlinkt den erfolgreichen CI-Gesamtlauf und den tatsächlich bestandenen
virtuellen Boot einschließlich RAMPI_BOOT_OK.

Keine erfolgreichen persönlichen Cloudanmeldungen, VPN-Netze, RDP-Desktops
oder Sunshine-Streams werden behauptet. Funk, HDMI, GPU-Leistung und echte
Eingabe-/Streaminglatenz sind außerhalb des vereinbarten Testumfangs.

Reproduzieren: pytest -q, python scripts/test-ui.py und die Docker-Aufrufe
in .github/workflows/ci.yml. Windows-SSH-/Installer-Tests verweigern Ausführung
außerhalb von GitHub CI. Imageprotokolle werden als Artefakte aufbewahrt.
Der Imageworkflow verwendet bei den Stagingquellen normale Benutzerbesitzrechte
und prüft danach root-eigene, für andere Benutzer schreibgeschützte Programmdateien.
Der QML-Test kontrolliert zusätzlich echte Latin-/Umlautglyphen und eine
gleichbreite Terminalschrift, damit ein Start mit fehlenden Fonts nicht genügt.

## Ergänzende Softwareabnahme: Streaming-Profile und WireGuard

Stand v0.2.2: 39 Python-Tests. Zusätzliche Prüfungen bestätigen die
Trennung von Moonlight-Kopplungspfaden zwischen Linux-Benutzern, Hosts und
Windows-Konten sowie den Einrichtungshinweis ohne persönliche Kopplung.

`scripts/test-wireguard.py` hat lokal unter Docker mit Debian Trixie amd64
einen echten Rundlauf durchgeführt: zwei getrennte Netzwerk-Namensräume,
NetworkManager und polkit, Rampi-Import und Aktivierung als normaler Benutzer,
private Profilrechte und deaktivierter Autostart, bidirektionaler verschlüsselter
Datenverkehr, WireGuard-Handshake und Transferzähler, Ablehnung eines falschen
Peer-Schlüssels sowie Trennung über den Rampi-Adapter. Die Testumgebung wird
anschließend entfernt. Die ARM64-CI führt denselben Test aus.

Reproduzieren:

```sh
docker build -t rampi-trixie-test -f tests/container/Dockerfile .
python scripts/test-wireguard.py
```

Die Container verwenden ein eigenes internes Docker-Netz und erhalten nur
NET_ADMIN/NET_RAW für ihre eigenen Netzwerk-Namensräume. Weder Hostnetzwerk noch
privilegierte Container sind nötig. Kurzlebige Schlüssel erzeugt das vorhandene
`wg`; sie werden weder ausgegeben noch in Git gespeichert. Die zusätzliche
polkit-Freigabe existiert nur in den wegwerfbaren Testcontainern.
Dies ist ein tatsächlicher privater VPN-Test, keine Anmeldung in einem persönlichen
Tailscale-Netz und kein Test gegen fremde oder persönliche Endpunkte.

## Ergänzung: Hostverwaltung und echte RDP-Verbindung

Stand v0.3.0: 45 Python-Tests. Zusätzliche Fälle prüfen mehrere
Hostprofile, Speicherung und Löschung, die Sperre beim laufenden Client sowie
das Verwerfen verspäteter Status-, Vorschau- und Fingerprintantworten eines
vorherigen Hosts. Der reale QML-Test speichert ein Profil durch die tatsächlichen
Formularaktionen, öffnet es erneut und prüft die Tastatursteuerung der Sitzungsseite.
Er verwendet ausschließlich ein temporäres persönliches Konfigurationsverzeichnis.

`scripts/test-rdp.py` hat lokal mit Docker/Trixie amd64 eine echte Verbindung
zwischen FreeRDP und xrdp/PAM bestanden: unabhängiger TLS-Fingerprintvergleich,
übertragene Desktop-Pixel, eingegebener Text beim authentifizierten Benutzer,
erneute Verbindung und Zurückweisung eines falschen Zertifikats. Server und
Client besitzen getrennte Netzwerk-Namensräume in einem internen Docker-Netz,
je 512 MB RAM und zwei CPUs. Keine Hostports, Geräte oder Hostdienste werden
freigegeben. Die ARM64-CI führt denselben Test aus.

```sh
docker build -t rampi-remote-test -f tests/remote/Dockerfile .
python scripts/test-rdp.py
```

Der Testserver erzwingt TLS; dies ist kein Nachweis für Windows-NLA oder die
Windows-Desktopintegration. Windows-CI prüft außerdem die tatsächlichen
Status-/Stop-Aktionen des persönlichen psmux-Adapters: Das exakt benannte Ziel
wird beendet, eine Sitzung mit gleichem Namenspräfix bleibt erhalten.

## Ergänzung: tatsächliche Sunshine/Moonlight-Verbindung

`scripts/test-streaming.py` hat lokal mit Debian Trixie amd64 die offizielle
Sunshine-Version 2026.914.233613 und denselben Moonlight-Embedded-2.7.1-Quellcommit
wie der Pi-Installer verbunden. Zwei normale Benutzerprozesse in getrennten
internen Docker-Netzwerk-Namensräumen führen die echte PIN-Kopplung aus. Ein
zweites, nicht gekoppeltes Rampi-Profil erhält keinen Anwendungszugriff. Der
Server verändert seine X11-Bildfläche fortlaufend; auf dem Client müssen beide
Farben nach echter H.264-Übertragung und SDL/FFmpeg-Decodierung ankommen, auch
nach erneuter Verbindung. Ein Start oder eine reine Logmeldung genügt nicht.

```sh
docker build -t rampi-streaming-test -f tests/streaming/Dockerfile .
python scripts/test-streaming.py
```

Die offiziellen amd64-/arm64-Sunshine-Pakete werden per veröffentlichtem SHA256
geprüft. Die ARM64-CI führt den gleichen Rundlauf aus. Jeder Container hat ein
1-GB-/Vier-CPU-Limit; Hostports und Hardwaregeräte werden nicht freigegeben.
Sunshines vorhandene stdin-PIN-Funktion ersetzt ausschließlich im wegwerfbaren
Test die manuelle Freigabe. Diese Abnahme belegt Linux-Softwarevideo und die
Protokollkopplung, keine Windows-Bildschirmaufnahme, GPU-Decodierung, Audio,
Streaming-Tastatureingabe oder gemessene Pi-Leistung. Sunshine bleibt eine
Freigabe der aktiven Konsole und schafft keine getrennte Windows-Anmeldung.

## Ergänzung: Kanban, persönliche VPN-Auswahl und tatsächlicher Streaming-Ton

Die Suite enthält 60 Python-Tests. Neue Fälle kombinieren Kanban-Filter und Suche,
erhalten unbekannte/leere Spalten, weisen ungültige Spaltenkonfigurationen vor der
Dateiersetzung zurück und verwerfen verspätete Antworten nach Quellenwechsel.
Der echte QML-Test liest eine JSON-Datei, wählt Filter mit der Tastatur, lädt die
Quelle erneut und speichert eine Spaltenreihenfolge durch die Einstellungsoberfläche.

Der echte WireGuard-Rundlauf prüft zusätzlich die neue persönliche Profilliste:
NetworkManager-D-Bus liefert den unveränderten Namen mit Sonderzeichen und den
vollständig aktivierten Zustand.
Gemeinsame Profile erscheinen nicht; ein anderes Linux-Konto sieht keine
persönlichen Einträge. Die UID-Zuordnung wird auch bei gefälschten USER-/LOGNAME-
Umgebungsvariablen geprüft. Ein weiterer echter QML-Test wählt das persönliche
Profil mit der Tastatur und aktiviert den tatsächlichen Tunnel über Enter.
Rampi verwendet für eigene Aktionsknöpfe den vorhandenen Qt-Button mit einer
einheitlichen Enter-Ergänzung. Enter, Ziffernblock-Enter und Leertaste lösen im
Oberflächentest jeweils genau eine Aktion aus.
Die Aktivierungs- und Berechtigungsprüfungen bleiben erhalten.

Der Sunshine-Test startet im isolierten Servercontainer einen privaten PulseAudio-
Null-Sink und dessen vorhandenes Sinusmodul mit 997 Hz. Sunshine nimmt den Ton auf
und überträgt ihn als Opus. Moonlight decodiert ihn über die unveränderte SDL-
Audioausgabe; SDLs vorhandener Disk-Treiber schreibt empfangene PCM-Samples im
Clientcontainer. Die Prüfung verlangt ausreichende Energie und Korrelation mit
997 Hz; separate Negativfälle verwerfen Stille und 440 Hz. Beide Verbindungen
müssen Videowechsel und Ton nachweisen. Das Testsignal folgt Sunshines virtuellem
Standardausgang. Keine Lautsprecher, Audiogeräte oder Host-Pulse-Sockets werden
freigegeben. Dies prüft Linux-Softwareaudio, keine Windows-WASAPI-Aufnahme,
Streaming-Tastatureingaben oder physische Audiolatenz.
