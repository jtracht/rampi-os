# Native Installation, Updates und Wiederherstellung

Zielsystem ist Raspberry Pi OS Lite Trixie ARM64 auf dem Pi 3 B+.
Der Installer verwendet ein vorab gebautes ARM64-Programm; er kompiliert nicht
auf dem Gerät. Es gibt noch kein reguläres natives Release. Verwende bis zur Freigabe einen
nachgewiesenen Entwicklungsbau. Verwende ausschließlich vollständig grüne CI-Läufe.
Das CI-Artefakt `native-installer-arm64` enthält
Quellarchiv, ARM64-Paket, Installer und Prüfsummen für denselben Stand.
Das einzelne veröffentlichte `setup.sh` lädt künftig beide passenden Archive über
HTTPS, prüft jede SHA256-Summe und gleicht Quellrevision und Binary ab, bevor der
Installer läuft. Es installiert niemals selbstständig zu einem späteren Zeitpunkt.

## Installation aus einem geprüften Checkout

Benötigt werden der Quellstand und das dazu gebaute `rampi-native`. Lege das
ausführbare Programm unter `native/bin/rampi-native` ab oder gib dessen absoluten
Pfad mit `RAMPI_NATIVE_BINARY` an. Anschließend:

```sh
bash setup.sh --check
sudo bash setup.sh --install
```

`--check` prüft Zielsystem, erforderliche Pakete und das vorhandene ARM64-Programm.
Fehlende Pakete werden erst bei der Installation ergänzt. Ein vorhandener
kompatibler Audioweg und vorhandene Login-Dienste werden berücksichtigt.
Aktive konkurrierende Netzwerkdienste führen zu einer klaren Fehlermeldung;
der Installer migriert diese nicht ohne ausdrückliche Einrichtung.

Ein eigenes Image verwendet `--image`; dieser Modus überspringt die physische
Modellerkennung und richtet einen neuen System-Login ein. Er ist kein
Hardware-Kompatibilitätstest und nicht der normale Aktualisierungsmodus.

## Versionswechsel und Reparatur

Updates erfolgen ausschließlich auf ausdrücklichen Aufruf:

```sh
sudo bash installer/raspberrypi/update.sh
```

Das Update verwendet den Quellstand und das vorab bereitgestellte Programm aus
diesem Checkout. Der Installer bereitet Programm und Grafiken gemeinsam unter
`/opt/rampi/` vor, prüft die Programmversion und aktiviert anschließend einen
vollständigen Versionsordner. Ein laufendes Programm wird nicht überschrieben.
Die Aktivierung des Links `current` erfolgt atomar. Die vorherige Version ist
über `previous` erreichbar. Parallele manuelle Installationen werden serialisiert.

Erneutes Installieren repariert die Programmdateien durch eine neue vorbereitete
Kopie. `setup.sh --repair` verwendet denselben Installationsweg. Persönliche
Konfigurationen, Schlüssel und Browserprofile werden dabei nicht ersetzt.
Die vorhandene Reparaturhilfe `installer/raspberrypi/repair.sh` führt zunächst
die Prüfung aus und nennt den ausdrücklich auszuführenden Reparaturaufruf.

## Rückkehr zur vorherigen Version

```sh
sudo bash installer/raspberrypi/rollback.sh
```

Die Hilfe prüft beide Versionsordner, Dateirechte und die gespeicherten
Programmprüfsummen. Eine manipulierte oder unvollständige vorherige Version
wird nicht aktiviert. Der Wechsel gilt für den nächsten Sitzungsstart; das
laufende Programm wird nicht beendet. Persönliche Einstellungen und globale
Systemkonfiguration werden nicht auf einen früheren Stand zurückgesetzt.
Versionsordner werden bewusst nicht automatisch gelöscht.

## Deinstallation

```sh
sudo bash installer/raspberrypi/uninstall.sh
```

Die Hilfe entfernt Rampi-Starter und Sitzungseinträge. Persönliche Daten,
Versionsordner und vorhandene Netzwerk-/Bluetooth-Dienste bleiben erhalten.
Wenn die unveränderte Login-Konfiguration nachweislich von Rampi stammt, wird
dieser Greeter deaktiviert und der reguläre TTY-Start gewählt. Fremde oder
nachträglich geänderte Login-Konfigurationen werden nicht ersetzt.

## Image-Bau und Nachweise

Der Image-Workflow baut das ARM64-Programm aus demselben Quellstand wie das Image.
Das festgehaltene offizielle pi-gen erstellt die Trixie-Basis. Im Image liegen
Programmprüfsumme, Quellrevision, Paketmanifest und Lizenzinformationen.
Die Rootfs-Prüfung kontrolliert Rust-Laufzeitbibliotheken, Wayland-Sitzung,
Dateirechte, Pi-Kernel und den Pi-3-B+-Gerätebaum.

Die nachfolgende QEMU-Prüfung kontrolliert Partitionen und Dateisysteme und
startet den Pi-Kernel bis zur Systemdiagnose. QEMU emuliert dabei einen Pi 3 B;
der separate Gerätebaum für den Pi 3 B+ wird im Image geprüft. Weder dieser
Test noch der Container-Belastungstest belegen Funk, HDMI, GPU-Decodierung oder
Geschwindigkeit auf einem physischen Pi. Physische Hardwaretests bleiben
vereinbarungsgemäß ausgeschlossen.

Der Freigabestatus unter `packaging/readiness.json` bleibt gesperrt, bis der
gesamte native Umfang und die erforderlichen Nachweise vorliegen.
