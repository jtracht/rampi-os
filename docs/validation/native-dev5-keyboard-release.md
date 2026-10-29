# Verifiziertes Tastatur-Folgerelease dev5

[Öffentliches Release](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.5), ausdrücklich eine Vorabversion.

- Unveränderter Tag-Quellstand: `81c0a4b8aea198206e0ae42d689b9c1cc81ae31a`.
- Endgültige allgemeine/native Push-CI: `40790022554` / `40790022564`.
- Frischer Image-/Release-Lauf: `40798235889`.
- Alle 28 tatsächlichen öffentlichen Dateien sind heruntergeladen und mit
  SHA256SUMS sowie vorhandenen GitHub-Digests geprüft.
- Image: `image_2026-10-29-rampi-os-rpi3bplus-v0.6.0-dev.5.img.xz`.
- Image-SHA256: `51b9d0bbf733ae6e9b9ebcd478d03bd61ca9f9438b4c6390bc3ab212c8ab2c4a`.
- Tatsächlich installiertes Release-ELF: `facecc9918928270b7c526b02eaadd6fafd6b9ed50c90bc9635e36b6f489655b`.

Die eingefrorenen Prüfer der akzeptierten Quelle bestätigen vollständige Rampi-,
Cargo-, Moonlight- und Distributionsquellen samt Lizenzen, Paket-/Programmzuordnung,
Kernelboot und grafische PAM-Anmeldung im neuen Image. Beide originalen Erstkonto-
Verfahren und ihre normalen Neustarts bestehen; das öffentliche grafische Archiv
enthält exakt 17 erlaubte Dateien. Private Fixture-Zugangsdaten werden nicht veröffentlicht.

Die native Prüfung beider Architekturen verlangt zusätzlich den wirklichen
labwc-Start mit doppelter Layout-Zuweisung und dessen `printenv`-Ergebnis. Der
GTK-/RDP-Code muss dazu dieselbe letzte Belegung verwenden, längere sichere
Konfigurationen lesen und eigene Einstellungen erhalten. [Fehler und lokale
Komponentenprüfung](keyboard-environment-consistency.md).

Der belegte Stand bleibt **91/95 = 95,8 %**. Ein einzelner behobener Randfall
schließt die vollständige Eingabe-/HID-Abnahme nicht ab. Die übrigen
[Abnahmegrenzen](../PROGRESS.md) bleiben offen; `regular_release=false`.
Der Auftrag bis 100 % wird getrennt weiterbearbeitet. Persönliche Rechner und
externe Windows-Testhosts bleiben ausgeschlossen; zusätzliche Windows-Komponenten
dürfen nach ausdrücklicher Nutzerklärung in isolierter GitHub-CI geprüft werden.
