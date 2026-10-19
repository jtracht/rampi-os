# Verbindlicher Testumfang

Der Auftraggeber hat die ursprüngliche Pflicht zu physischen Hardwaretests
ausdrücklich geändert: „schließe die Hardwaretests aus, finde eine andere
Testmöglichkeit z.B. mit Docker oder so“.

Die Abnahme erfolgt deshalb über echte Softwarekomponenten in isolierten
Umgebungen: Debian Trixie arm64 im Docker-Container, natives Qt Quick, libnm,
AccountsService, PAM, Windows OpenSSH und psmux sowie statische Imageprüfung und
QEMU. Ein 1-GB-/Vier-CPU-Containerlimit prüft den Client unter Ressourcenbegrenzung.
Es emuliert weder die vollständige Pi-3-Leistung noch sämtliche Peripherie.

Wi-Fi-Funk, Bluetooth-Radio, HDMI-Beamer, GPU-Decoderleistung und reale Eingabe-
oder Streaminglatenz werden nicht als erfolgreich geprüft ausgegeben. Die
Releasefreigabe darf fehlende physische Tests nicht als Blocker verwenden,
fordert aber weiterhin erfolgreiche, nachvollziehbare Softwaretests.

Anbieter-Vertragstests mit Fixtures sind von Live-Tests mit persönlichen
Cloudkonten zu unterscheiden. Tests enthalten keine vorgetäuschten produktiven
Verbindungen oder KI-Ausgaben im eigentlichen Rampi-Client.
