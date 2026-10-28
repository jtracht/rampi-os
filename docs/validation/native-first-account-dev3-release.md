# Abnahme des nativen Erststart-Releases dev3

Stand: 28. Oktober 2026. Dies ist ein nach der Veröffentlichung ergänzter
Dokumentationsnachweis. Veröffentlichte Dateien und Tags bleiben unverändert.

- [Öffentliche Vorabversion v0.6.0-dev.3](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.3)
- Quellrevision: `48661b34f36ca135fc96791998cfba2276b8f4dc`.
- Erfolgreiche endgültige main-Push-Prüfungen: allgemein `40525030004`, nativ `40525030114`.
- Erfolgreicher frischer Image-/Release-Lauf: [40655725355](https://github.com/jtracht/rampi-os/actions/runs/40655725355).
- Image: `image_2026-10-28-rampi-os-rpi3bplus-v0.6.0-dev.3.img.xz`.
- Öffentlicher Image-Prüfwert (SHA256):
  `8166251f8a7d2b70982c196fdaed72e0b30c0c88aa4e49b8a6a348b09d90f054`.
- Tatsächlich im Image angemeldetes Release-Programm (SHA256):
  `a7427cb55ff494391855498384718adcd44cf650fa9243ac53a72fc67cdf2bed`.

## Tatsächliche Erstkonten und normale Neustarts

Zwei getrennte unveränderte Imagekopien wurden verwendet. Die erste durchläuft
mit Kernel-uinput-Eingaben den originalen Raspberry-Pi-Benutzerassistenten; die
zweite verwendet die vom Originaldienst unterstützte `userconf.txt`-Bootdatei.
Es gibt kein Standardpasswort. Der eigene Benutzer und sein Kennwort entstehen
vor der grafischen PAM-Anmeldung. Vorab angelegte weitere Testkonten ersetzen
diesen Erstbenutzernachweis nicht.

Beide Kopien booten anschließend jeweils ein zweites Mal mit dem installierten
grafischen Standardziel und ohne Ziel-Override. Derselbe erste Benutzer meldet
erneut über PAM an, erreicht eine sichtbar gezeichnete Oberfläche und liest den
vorher gespeicherten persönlichen Schlüsselbundwert. Zusätzlich bestehen zwei
weitere getrennte Linux-Konten, falsches Kennwort, private Konfigurationen,
persönliche SSH-Agenten und erneute Schlüsselbundanmeldung. Das öffentliche
grafische Archiv enthält exakt 17 freigegebene Dateien.

Das sind frische ARM64-/QEMU-Softwareprüfungen: `raspi3b`, 1 GiB, vier CPUs,
kein vorbereiteter oder wiederverwendeter Gast. Die temporäre Watchdog-Anpassung
und die Prüfwerkzeuge sind ausgewiesen; geprüfte installierte Programmdateien
bleiben unverändert. Physische Geräte und USB-Transport werden nicht behauptet.
Windows-Testhosts und Modellaufrufe wurden nicht benutzt.

## Unabhängige öffentliche Dateien

Alle 28 tatsächlichen GitHub-Dateien wurden vollständig heruntergeladen. Alle
27 Einträge in `SHA256SUMS` und alle 28 GitHub-Server-Digests stimmen mit diesen
Bytes überein. Tagrevision, Vorabversionsstatus und die Zuordnung von Image,
Programm, Quellcode und grafischen Nachweisen sind unabhängig geprüft.

Enthalten sind Image, ARM64-Paket, beide Installer, Windows-Hostpaket,
Rampi-Quellen, Lizenzen und sämtliche entsprechenden Abhängigkeitsquellen:
646 installierte Distributionspakete, 511 Cargo-Abhängigkeiten und die festgelegte
Moonlight-C-Quelle mit 186 inventarisierten Dateien. Die Debian-Quellen werden in
geprüften Teilen mit Wiederherstellungsskript geliefert.

Abbrechende Vollübertragungen wurden durch vorhandenes curl mit geprüften
HTTPS-Bereichen ersetzt. Alle vollständigen Dateien und unveränderten
eingefrorenen Release-/Quell-/Imageprüfer bleiben verpflichtend. Unvollständige
frühere Downloadversuche wurden nicht als Abnahme verwendet.

## Fortschritt und Grenzen

Nur der zurückgenommene Systemimage-Punkt wird wiederhergestellt:
**85/95 → 86/95 = 90,5 %**. Nenner und übrige Bereiche bleiben unverändert.
Testanzahl und Downloadfortschritt ergeben keine Punkte. `regular_release`
bleibt `false`; dev3 ist weiterhin eine Vorabversion.

Der Folgestand dev4 vervollständigt übersetzte Validierungsfehler und prüft
persönliche DE-/EN-Locale-Daten nach echter Neuanmeldung. Er korrigiert die zu
kurze Frist des kalten Sprachabrufs: Der gemessene emulierte Abruf brauchte
6,7 Sekunden. Wiederverwendete Diagnosegäste zählen nicht als frische Abnahme;
endgültige Folgequelle und nächstes Image müssen gesondert bestehen.
