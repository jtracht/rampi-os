# Installation auf Raspberry Pi

Ziel ist Raspberry Pi OS Lite Trixie arm64 auf Pi 3 Model B+. Aktuelle Images
mit Raspberry Pi Imager beziehen; Benutzer, Zeitzone, Sprache und Tastatur dort
einrichten. USB-Tastatur für die erste Bluetooth-Kopplung bereithalten.

Das vollständige Quellpaket entpacken, darin `bash setup.sh --check` ausführen.
Nach Prüfung `sudo bash setup.sh --install`. Das einzelne setup.sh lädt in einem
veröffentlichten Release das versionsgleiche Quellpaket und prüft dessen
veröffentlichte SHA-256-Prüfsumme vor der Installation.

Das Skript verwendet Debian-Pakete, installiert nur fehlende Pakete und stoppt
bei aktiven konkurrierenden Netzwerkmanagern. Es ersetzt keine vorhandene
Openbox-, LightDM-, PAM- oder Bootkonfiguration. Die Rampi-Sitzung wird zusätzlich
registriert. Im bestehenden Loginbildschirm **Rampi** wählen. Eine Lite-Installation
ohne aktiven Displaymanager benötigt anschließend die bewusste Aktivierung von
LightDM (`sudo systemctl enable --now lightdm`). Bestehende Displaymanager nicht
parallel starten.

`installer/raspberrypi/update.sh` installiert den bewusst heruntergeladenen neuen
Quellstand. Es gibt keinen Update-Timer. `repair.sh` prüft Voraussetzungen;
`diagnostics.sh` sammelt nicht geheime Systemdaten. `uninstall.sh` entfernt nur die
Sitzungsintegration. Persönliche Daten und gemeinsame Pakete bleiben erhalten.

`--install --with-extras` ergänzt fehlendes Tailscale aus dem signierten offiziellen
Repository und baut fehlendes Moonlight Embedded aus einem festgelegten offiziellen
Commit. Vorhandene Installationen bleiben erhalten. Im Image sind diese Komponenten
enthalten. Der SDL-/FFmpeg-Pfad verwendet die bestehende X11-Sitzung und benötigt
keine Änderungen an KMS-/FKMS-Firmwareoptionen. Entsprechende Moonlight-Quellen
werden mitgeliefert. Updates bleiben manuell.
