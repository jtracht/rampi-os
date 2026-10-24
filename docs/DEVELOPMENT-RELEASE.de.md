# Native Entwicklungsreleases

Ein Entwicklungsrelease veröffentlicht den vorhandenen geprüften Rust-Stand,
ohne vollständige Produktreife vorzutäuschen. `regular_release` bleibt `false`;
die automatische Freigabe regulärer Releases wird dadurch nicht aktiviert.
Die vorhandene Versionsnummer `0.6.0-dev.1` bezeichnet das erste native
Entwicklungsrelease und ist bislang noch nicht als öffentlicher Git-Tag erschienen.

Der manuell gestartete GitHub-Workflow **Native development release** arbeitet
ausschließlich auf `main`. Er verlangt eine ausdrückliche SemVer-Vorabversion,
einen noch nicht vorhandenen Tag und vollständig erfolgreiche allgemeine und
native Push-Prüfungen genau derselben Quellrevision. Danach verwendet er den
vorhandenen Image-Workflow für einen neuen ARM64-/pi-gen-Bau.

Vor der Veröffentlichung sind sowohl der Softwareboot als auch die grafische
Anmeldung im tatsächlich installierten Image Pflicht: zwei Linux-Konten, private
Profile, sichtbare Oberfläche, falsches Kennwort und unveränderte Programmdateien.
Image, Paketprogramm, Quellarchiv und CI müssen dieselbe Revision belegen.
Der explizit verwendete QEMU-Modus wird auch im Image-Nachweis dokumentiert.
Physische Hardwaretests bleiben wie vereinbart ausgeschlossen.

Veröffentlicht werden mindestens:

- Flashbares `.img.xz` und passendes natives ARM64-Paket.
- Vollständiger Quellcode, `setup.sh`, `setup.ps1` und Windows-Hostpaket.
- Prüfsummen, Paketmanifest, originale Abhängigkeitslizenzen und Quellzuordnung.
- Softwareboot- und grafische Anmeldenachweise sowie die konkrete CI-Zuordnung.
- `development-release.json` mit Quellrevision, Version, Image- und Programmhash.

Der Publisher erzeugt den Tag erst nach erfolgreicher Artefaktprüfung atomar
über GitHub. Zunächst entsteht ein Entwurf; anschließend wird derselbe Release
ausdrücklich als Vorabversion veröffentlicht. Bestehende Tags oder Releases
werden nicht ersetzt. Unterbrochene Veröffentlichungen müssen anhand derselben
Revision und Artefakte geprüft werden; ein neuer Aufruf überschreibt sie nicht.
Der Geräte-Installer installiert Updates weiterhin ausschließlich manuell.

Die Release-Hinweise nennen die verbleibenden Funktionen und Prüfgrenzen.
Insbesondere entstehen dadurch keine angeblich abgeschlossenen Streaming-,
Windows-11-Pro- oder persönlichen Anbieterabnahmen. Modellanfragen bleiben
ausgeschlossen. Die eigentliche neue Streaming-Integration bleibt währenddessen
in ihrem gesonderten Entwicklungszweig und wird nicht ungeprüft in das Image
übernommen.
