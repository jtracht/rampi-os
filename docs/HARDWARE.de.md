# Raspberry Pi 3 und neuer

Rampi OS richtet sich an die ARM64-fähigen Raspberry-Pi-Familien ab Pi 3.
Ein gemeinsames Raspberry Pi OS Lite Trixie ARM64-Image verwendet die vorhandene
Firmware zur Auswahl des passenden Kernels und Gerätebaums. Der neue Dateiname
lautet `rampi-os-rpi-arm64-vX.Y.Z.img.xz`; bereits veröffentlichte Dateien behalten
ihren Namen und ihre bisherigen Nachweise.

| Familie | Zielmodelle | Ressourcen und Ausstattung |
| --- | --- | --- |
| Pi 3 | 3 B, 3 B+, 3 A+ | Sparsames Basisprofil; A+ hat nur 512 MB |
| Pi 4 | 4 B, 400 | Gleiche ARM64-Anwendung, vorhandene modellgerechte Treiber |
| Pi 5 | 5, 500, 500+ | Plattformkernel kernel_2712.img; keine Pi-3-Bootparameter erzwingen |
| Compute Module | CM3/3+, CM4/4S, CM5 | Passendes Carrierboard, Bildausgang und Netzwerk erforderlich |
| Zusätzlich | Zero 2 W | ARM64-fähig, 512 MB; eingeschränkte parallele Browser-/Remote-Nutzung |

Pi 1, Pi 2, ursprüngliche Zero/Zero W und Pico gehören nicht zur Zielplattform.
Eine spätere Modellgeneration wird erst nach Prüfung ihrer Betriebssystembasis
aufgenommen. „Ab Pi 3“ ist keine Zusage für unbekannte künftige Hardware.

## Gemeinsame Optimierung

Die Rust-Anwendung bleibt für generisches AArch64 gebaut: keine `target-cpu=native`
oder Pi-5-Instruktionen, die Pi 3 ausschließen. GTK/Wayland und labwc ersetzen eine
vollständige Desktopumgebung. Animationen zeichnen nur bei Bedarf und begrenzen
aufwendige Zeichenanforderungen auf etwa 30 pro Sekunde; reduzierte Bewegung ist
verfügbar. Das konservative Cairo-Profil bleibt modellübergreifend erhalten.
Browser und Remote-Sitzungen werden bedarfsgerecht gestartet. Auf 512-MB-Modellen
sollen ressourcenintensive Inhalte einzeln verwendet werden; eine flüssige
Browser-/Streaming-Nutzung unter allen Lasten ist nicht abgenommen.

Der Installer prüft ARM64, Trixie und die Modellfamilie. Er erzwingt weder Takt,
GPU-Speicher, Kernel noch Display-Bootoptionen. Bestehende Konfigurationen bleiben
erhalten. WLAN und Bluetooth benötigen tatsächlich vorhandene Adapter; Compute
Modules besitzen abhängig von Variante und Carrierboard nicht dieselbe Ausstattung.

## Automatisierte Prüfung und Grenzen

Der Image-Test verlangt die Bootdateien der Pi-3-, Pi-4- und Pi-5-Familien.
Modellerkennung wird einschließlich nicht unterstützter Geräte automatisiert
geprüft. Die bisherigen grafischen QEMU-Nachweise emulieren Pi 3 B; sie sind
keine Laufzeit- oder Leistungsabnahme für Pi 4/5, Keyboard- oder Compute-Modelle.
ARM64-CI, Container und QEMU prüfen Software; physische Hardwaretests bleiben auf
Nutzerwunsch ausgeschlossen. Vor einer Veröffentlichung muss das neu gebaute
Image alle bestehenden Quellen-, Anmelde- und Zuordnungsprüfungen bestehen.
Historische Testberichte und Screenshots werden nicht rückwirkend umbenannt.

Quellen: [Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html),
[Kernelplattformen](https://www.raspberrypi.com/documentation/computers/linux_kernel.html),
[offizielle Bootdateien](https://github.com/raspberrypi/firmware/tree/master/boot).
