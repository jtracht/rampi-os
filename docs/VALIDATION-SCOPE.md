> Historischer Stand vor der Produktänderung vom 26.10.2026. Direkte KI-Module
> und ihre Windows-Sitzungsverwaltung sind entfernt. Für aktuelle Funktionen,
> Bedienung und Prüfgrenzen gelten [Umfang](NATIVE-SUPPORT.de.md),
> [Bedienung](NATIVE-USER-GUIDE.de.md) und [Fortschritt](PROGRESS.md).

# Verbindlicher Testumfang

Der Auftraggeber hat die ursprüngliche Pflicht zu physischen Hardwaretests
ausdrücklich geändert: „schließe die Hardwaretests aus, finde eine andere
Testmöglichkeit z.B. mit Docker oder so“.

Die Abnahme erfolgt deshalb über echte Softwarekomponenten in isolierten
Umgebungen: Debian Trixie auf AMD64 und ARM64 in Docker und QEMU, die tatsächliche
Rust-/GTK4-/Wayland-Sitzung mit labwc, VTE und WebKit, libnm/NetworkManager,
BlueZ, Linux-Systemkonten und PAM, Windows OpenSSH und psmux sowie die Prüfung
des tatsächlich gebauten Raspberry-Pi-Images. Historische Qt-/QML-Nachweise
ersetzen keine native Rust-Abnahme. Ein 1-GiB-/Vier-CPU-Limit prüft den Client unter Ressourcenbegrenzung.
Es emuliert weder die vollständige Pi-3-Leistung noch sämtliche Peripherie.

Vorhandene virtuelle Kernel-Radios prüfen tatsächliche WLAN-Authentifizierung,
DHCP und IP-Verkehr sowie BlueZ-Kopplung und Bond-Dateien. Das ist keine Prüfung
physischer Funkübertragung. HDMI-Beamer, Pi-GPU-Decoderleistung und reale Eingabe-
oder Streaminglatenz werden nicht als erfolgreich geprüft ausgegeben. Die
Releasefreigabe darf fehlende physische Tests nicht als Blocker verwenden,
fordert aber weiterhin erfolgreiche, nachvollziehbare Softwaretests.

Anbieter-Vertragstests mit Fixtures sind von Live-Tests mit persönlichen
Cloudkonten zu unterscheiden. Tests enthalten keine vorgetäuschten produktiven
Verbindungen oder KI-Ausgaben im eigentlichen Rampi-Client.

## Aktuelle Grenzen persönlicher Live-Prüfungen · 24.10.2026

Der Auftraggeber hat ausdrücklich festgelegt: **Noch keine Modellanfragen
auslösen.** Es werden deshalb weder kostenpflichtige noch kostenlose
Anbieteranfragen zu Testzwecken gestartet. Versions-/Installationsprüfungen und
isolierte Terminaltests sind davon getrennt; sie belegen keine Anbieteranmeldung
oder tatsächliche Modellantwort. Der echte Windows-SSH-Persistenztest verwendet
ein ausdrücklich bezeichnetes Heartbeat-Programm.

Ein Windows-11-Pro-Testhost ist laut Auftraggeber nicht vorhanden. Die
Windows-CI mit kurzlebigen Konten auf GitHub-Runnern belegt die tatsächlich
geprüften OpenSSH-/ConPTY-/psmux-Abläufe auf diesem Betriebssystem. Sie ersetzt
keine zusammenhängende Abnahme am vorgesehenen Windows-11-Pro-Host. Es werden
dafür keine Systemdienste oder Konten auf dem persönlichen Arbeitsrechner
eingerichtet. Unabhängige lokale und virtuelle Arbeiten gehen weiter.

Ein grüner Einzeltest ersetzt keine vollständige Freigabe. Fortschritt und
Releasebereitschaft richten sich nach [PROGRESS.md](PROGRESS.md), der nativen
Funktionsmatrix und den ausdrücklich genannten heruntergeladenen Nachweisen.
