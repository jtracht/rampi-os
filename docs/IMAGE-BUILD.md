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
muss vor Nutzung ein eigenes Konto anlegen. Das Verhalten mit LightDM muss auf
echter Hardware geprüft werden. Eine vollständig eigene grafische Erstkontoanlage
ist noch nicht implementiert.

`verify-rootfs.sh` prüft Rampi-Dateien, arm64, Boot-Dateien, Pi-3-B+-DTB und
grundlegende Dateirechte. pi-gen erstellt Partitionen und Dateisysteme. Eine
separate automatische Prüfung des finalen Partitionslayouts sowie Flash-/Boottest
fehlen noch. Das Image ist deshalb ein Kandidat, keine Hardwarefreigabe.

Paketmanifest wird im Image unter `/opt/rampi/package-manifest.tsv` gespeichert.
Der Buildpfad ist wiederholbar, aber wegen veränderlicher Paketquellen und
Zeitstempel noch nicht bitweise reproduzierbar. Paket-Snapshots und festgelegte
Rootfs-/Containerquellen sind vor regulärer Freigabe nachzurüsten.
