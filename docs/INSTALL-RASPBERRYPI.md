# Installation auf Raspberry Pi

Der aktuelle Entwicklungsstand verwendet **Rust, GTK 4 und Wayland/labwc**.
`startx`, Xorg, Openbox und LightDM werden dafür nicht eingerichtet.
Die veröffentlichte Version v0.5.0 gehört zum früheren Python-/QML-Prototyp;
ein reguläres natives Release ist noch nicht freigegeben.

Ziel ist Raspberry Pi OS Lite Trixie ARM64 auf dem Raspberry Pi 3 B+.
Benutzerkonto, Zeitzone und Tastatur zunächst mit Raspberry Pi Imager einrichten.
Die erste Bluetooth-Kopplung kann eine USB-Tastatur erfordern.

Verwende ausschließlich zusammengehörige native Entwicklungsartefakte:
Quellarchiv, `rampi-linux-arm64-VERSION.tar.xz`, `setup.sh` und `SHA256SUMS`.
Nach Prüfsummenvergleich das Quellarchiv entpacken und das ARM64-Paket in dessen
Ordner `native/` entpacken. Dort muss `native/bin/rampi-native` liegen. Dann:

```sh
bash setup.sh --check
sudo bash setup.sh --install
```

Ein einzelnes Release-`setup.sh` lädt das exakt versionsgleiche Quell- und
ARM64-Paket von GitHub. Vor der Installation prüft es Prüfsummen, sichere
Archiveinträge und übereinstimmende Quellrevisionen. Bis ein entsprechendes
natives Release veröffentlicht ist, die vollständigen Entwicklungsartefakte
verwenden. Ein bloßer Git-Checkout enthält kein fertig gebautes ARM64-Programm.

Der Installer erkennt vorhandene Pakete und kompatible Dienste. Auf Lite kann er
greetd/wlgreet als Anmeldung einrichten; ein vorhandener fremder Login-Dienst
bleibt erhalten. Keine konkurrierenden Display- oder Netzwerkmanager aktivieren.
Persönliche Konfigurationen liegen im jeweiligen Linux-Konto.

Updates werden ausschließlich bewusst manuell installiert. Reparatur,
versionierte Aktivierung, Rückwechsel, Entfernung und Grenzen stehen in
[Native Installation und Wiederherstellung](NATIVE-OPERATIONS.de.md).
Die [Bedienungsanleitung](NATIVE-USER-GUIDE.de.md) führt vom ersten Start über
Netzwerk und Windows-Host bis zu den Modulen. Den aktuellen Stand und offene
Integrationen nennt die [native Funktionsmatrix](NATIVE-SUPPORT.de.md).

Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen. CI, QEMU und
Docker liefern Softwarebelege; sie bestätigen keine physische Funk-, HDMI-
oder GPU-Eigenschaft.
