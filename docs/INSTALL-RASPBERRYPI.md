# Installation auf Raspberry Pi

Ziel ist Raspberry Pi OS Lite Trixie arm64 auf Pi 3 Model B+. Aktuelle Images
mit Raspberry Pi Imager beziehen; Benutzer, Zeitzone, Sprache und Tastatur dort
einrichten. USB-Tastatur für die erste Bluetooth-Kopplung bereithalten.

Das vollständige Quellpaket entpacken, darin `bash setup.sh --check` ausführen.
Nach Prüfung `sudo bash setup.sh --install`. Das einzelne setup.sh benötigt
derzeit den restlichen Quellbaum; es lädt nicht ungeprüft Code nach.

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

Tailscale und Moonlight werden noch nicht automatisch aus Fremdquellen installiert.
Die im Netzwerk-/Streamingdokument verlinkten offiziellen Wege verwenden und
Version/Kompatibilität vor der Aktivierung prüfen. Der Installer stellt daher
noch nicht alle geforderten Module vollständig bereit.
