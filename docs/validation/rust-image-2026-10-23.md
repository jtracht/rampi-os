# Erstes natives Rust-/Wayland-Entwicklungsimage

Das tatsächliche flashbare ARM64-/Trixie-Image ist gebaut, heruntergeladen,
per SHA256 geprüft und zweimal mit dem Pi-Kernel in QEMU gestartet.
Es ist ein Entwicklungskandidat, kein reguläres Release.

| Zuordnung | Wert |
|---|---|
| Image-Quellstand | `acc8eb36061f59231edad90edd0d4b4ecdc3e0b4` |
| [Bau und erste QEMU-Abnahme](https://github.com/jtracht/rampi-os/actions/runs/39868981832) | beide Jobs erfolgreich |
| [Erweiterte Herkunftsprüfung und erneuter QEMU-Boot](https://github.com/jtracht/rampi-os/actions/runs/39871180958) | erfolgreich |
| Erweiterter Prüfstand | `ec7a88e65ab4aa9721fd3c68f3d29143f054e172` |
| Dateiname | `image_2026-10-22-rampi-os-rpi3bplus-v0.6.0-dev.1.img.xz` |
| Komprimierte Größe | 775.200.488 Byte |

SHA256 des heruntergeladenen Images:

```text
71f4ef796443855503f9a1fd3a45df43d9e721fe08f6b64f5e6b866e53a17be0
```

SHA256 des tatsächlich im Image installierten ARM64-Rust-Programms:

```text
5203292055d71c7a64ab54c459a4ee05f4606403098409e71a3f31527ec2f66b
```

## Umfang der Prüfung

Der Image-Bau kompiliert das Programm mit dem festgehaltenen Cargo-Lockfile
nativ auf ARM64. Das gepinnte offizielle pi-gen erstellt die Trixie-Basis und
führt den tatsächlichen nativen Installer aus. Die Rootfs-Prüfung kontrolliert
Programm, passende Grafiken, Wayland-Sitzung, erforderliche Bibliotheken,
Dateirechte und Pi-Kernel/Gerätebäume. Die ursprünglichen Lizenztexte der
aufgelösten Cargo-Abhängigkeiten, Rust-Standardbibliothek und Distributionspakete
sind enthalten, mit Paket-/Versionsmanifest.

Die erweiterte Abnahme kontrolliert zusätzlich die heruntergeladene Image-Datei,
den eingebetteten Quellstand gegen den erzeugenden GitHub-Lauf, die Prüfsumme
des tatsächlich ausgewählten ARM64-Programms und die vorhandenen nativen
Sitzungs-/Lizenzdateien. Der Pi-3-B+-Gerätebaum ist vorhanden. FAT-/ext4-Prüfungen
und Partitionstabelle bestehen.

QEMU verwendet `raspi3b`, vier CPUs und 1 GiB, den tatsächlichen Pi-Kernel und
das mitgelieferte Initramfs. Nur die temporäre QEMU-Gerätebaumkopie deaktiviert
den emulierten Watchdog, weil QEMU dessen Entschärfung als Reset interpretiert.
Das ursprüngliche Image wird schreibgeschützt geprüft und für den Lauf nur
über einen temporären Snapshot verändert.

Der zweite Lauf erreicht nach rund 180 Sekunden emulierter Bootzeit:

```text
Rampi 0.6.0-dev.1 (Rust / Wayland)
RAMPI_BOOT_OK
```

Die heruntergeladenen Logs, Paket-/Lizenzarchive und Herkunftsdatei wurden
separat kontrolliert. Die SHA256 des vollständigen lokalen Image-Downloads
stimmt ebenfalls mit dem Producer-Manifest überein.

## Grenzen und nachfolgender Quellstand

Der Boot läuft bis zur Systemdiagnose im Mehrbenutzermodus, nicht durch eine
vollständige grafische PAM-Anmeldung. Es ist kein Nachweis für Funk, HDMI,
GPU-Decodierung oder physische Pi-Geschwindigkeit. Physische Hardwaretests sind
vereinbarungsgemäß ausgeschlossen; QEMU emuliert Pi 3 B, nicht sämtliche
Pi-3-B+-Peripherie.

Die Rust-Programmquellen sind zwischen Image-Producer und erweitertem Prüfstand
unverändert. Spätere Änderungen an manuellen Installerhilfen und zusätzlichen
Tests sind keine nachträgliche Änderung dieses Images. Deren separate
[ARM64-Abnahme](rust-native-2026-10-23.md) ersetzt keinen neuen vollständigen
Release-Bau. `regular_release` bleibt ausdrücklich `false`.
