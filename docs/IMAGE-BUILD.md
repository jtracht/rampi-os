# Image-Build

Der Imageworkflow verwendet den offiziellen RPi-Distro/pi-gen-arm64-Quellbaum,
festgelegt in `image/pi-gen-revision`. Basis: Lite-Stages 0–2, Trixie arm64,
zusätzliche Stage für Rampi. Ein vorhandenes Image-Buildsystem wird wiederverwendet.

Auf einem geeigneten Linux-ARM64-Rechner mit Docker `bash image/build.sh`
aus einem sauberen, committed Checkout ausführen. GitHub Actions bietet denselben
Workflow **Image candidate**. Der Build verändert keine lokalen Datenträger;
pi-gen benötigt privilegierte Container für seine Loop-/Mount-Arbeit.

Kein festes Kennwort, kein persönlicher SSH-Schlüssel, SSH beim Image deaktiviert.
Der temporäre Benutzer ist gesperrt; die vorhandene Raspberry-Pi-Ersteinrichtung
muss vor Nutzung ein eigenes Konto anlegen. Alternativ das eigene Konto mit
Raspberry Pi Imager vorkonfigurieren. Weitere Konten legt die grafische Rampi-
Oberfläche über AccountsService/PAM an. Physische Hardwaretests sind gemäß
`VALIDATION-SCOPE.md` ausgeschlossen.

`verify-rootfs.sh` prüft Rampi-Dateien, arm64, Boot-Dateien, Pi-3-B+-DTB und
grundlegende Dateirechte. pi-gen erstellt Partitionen und Dateisysteme.
`test-image.sh` prüft das exportierte Partitionslayout, FAT und ext4 sowie
Bootdateien und führt einen zeitbegrenzten QEMU-Startversuch durch. Erfolgsmarker
ist `RAMPI_BOOT_OK` aus dem echten systemd-Healthcheck im Gast. Der getrennte
Validierungsjob bewahrt Logs auf; fehlgeschlagene Validierung verhindert Releases.
Ein Flash- oder physischer Pi-Boot wird nicht behauptet.

Die virtuelle raspi3b-Maschine verwendet den originalen Pi-Kernel und das
originale initramfs. Nur eine temporäre DTB-Kopie deaktiviert den Watchdog:
QEMU 8.2 interpretiert dessen Deaktivierungszugriff als sofortigen Reset
(siehe upstream hw/misc/bcm2835_powermgt.c). Der Test verwendet die im DTB
als serial1 bezeichnete PL011-Konsole ttyAMA1. Das ausgelieferte Image und
seine DTB bleiben unverändert; Laufzeitschreibzugriffe gehen in einen
temporären Snapshot. qemu-environment.txt dokumentiert diese Testanpassung.

Paketmanifest wird im Image unter `/opt/rampi/package-manifest.tsv` gespeichert.
Der Buildpfad ist wiederholbar, aber wegen veränderlicher Paketquellen und
Zeitstempel noch nicht bitweise reproduzierbar. Paket-Snapshots und festgelegte
Rootfs-/Containerquellen sind vor regulärer Freigabe nachzurüsten.
