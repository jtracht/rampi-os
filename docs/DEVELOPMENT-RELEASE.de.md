# Native Entwicklungsreleases

Ein Entwicklungsrelease veröffentlicht den vorhandenen geprüften Rust-Stand,
ohne vollständige Produktreife vorzutäuschen. `regular_release` bleibt `false`;
die automatische Freigabe regulärer Releases wird dadurch nicht aktiviert.
`0.6.0-dev.1` und `0.6.0-dev.2` sind bereits veröffentlichte Vorabversionen und
bleiben unverändert. `0.6.0-dev.3` ist veröffentlicht und unabhängig geprüft; siehe
[Erststart-Abnahme](validation/native-first-account-dev3-release.md).
Der Folgestand dieses Zweigs ist `0.6.0-dev.4`. Die Zwischenveröffentlichungen
sind vom Nutzer freigegeben; eine laufende Prüfung ist noch keine Veröffentlichung. Ein aktualisierter Versionswert
oder erfolgreicher Komponentenlauf bestätigt noch keine Veröffentlichung.

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

Für dev3 und alle folgenden nativen Releases muss zusätzlich das tatsächliche erste Konto auf zwei getrennten frischen
Imagekopien entstehen: einmal mit dem originalen interaktiven Assistenten, einmal
über die unterstützte `userconf.txt`-Bootdatei. Beide Konten müssen nach einem zweiten
normalen Kernel-Boot erneut über PAM anmelden und den gespeicherten Schlüsselbundwert
lesen. Ein neu erstelltes Testkonto ersetzt diese Erststartprüfung nicht.

Veröffentlicht werden mindestens:

- Flashbares `.img.xz` und passendes natives ARM64-Paket.
- Vollständiger Quellcode, `setup.sh`, `setup.ps1` und Windows-Hostpaket.
- Prüfsummen, Paketmanifest, originale Abhängigkeitslizenzen und Quellzuordnung.
- Exakte Distributions-Quellarchive mit signiertem Indexbezug und vollständige
  Cargo-Abhängigkeitsquellen mit Registry-Prüfsummen und festgelegten Git-Revisionen.
- Softwareboot- und grafische Anmeldenachweise sowie die konkrete CI-Zuordnung.
- `development-release.json` mit Quellrevision, Version, Image- und Programmhash.

Der Publisher erzeugt den Tag erst nach erfolgreicher Artefaktprüfung atomar
über GitHub. Zunächst entsteht ein Entwurf; anschließend wird derselbe Release
ausdrücklich als Vorabversion veröffentlicht. Bestehende Tags oder Releases
werden nicht ersetzt. Unterbrochene Veröffentlichungen müssen anhand derselben
Revision und Artefakte geprüft werden; ein neuer Aufruf überschreibt sie nicht.
Der Geräte-Installer installiert Updates weiterhin ausschließlich manuell.

Der neue Imagebau übernimmt die Lite-Paketauswahl des festgelegten pi-gen und
entfernt daraus vor der Installation ausschließlich `rpi-connect-lite`. Rampi
benötigt dessen zusätzlichen Cloud-Fernzugriffsdienst nicht. Für Version 2.14.0
enthält der signierte Raspberry-Pi-APT-Index das Binärpaket, aber kein zugehöriges
Quellpaket. Der erste native Release-Lauf wurde deshalb von der vollständigen
Quellenprüfung gestoppt. Die Prüfung bleibt für sämtliche tatsächlich
installierten Pakete bestehen. Andere Lite-Pakete einschließlich `rpifwcrypto`
bleiben erhalten; Letzteres hat das vorhandene Quellpaket `raspi-utils`.
Der Installer auf bestehenden Geräten entfernt keine vorhandenen Dienste.

Für die ältere Bibliotheks-ABI `libwlroots-0.18` verwendet ausschließlich das
neu gebaute Image die weiterhin gepflegten Debian-Trixie-Pakete. Im geprüften
Raspberry-Pi-Index blieb das Binärpaket `0.18.2-3+rpt4+b1` verfügbar, dessen
Quellversion `0.18.2-3+rpt4` jedoch nicht; der zweite Release-Bau stoppte deshalb
ebenfalls korrekt. Eine auf genau diesen Paketnamen beschränkte APT-Präferenz
bevorzugt die signierten Debian-Pakete mit vollständigem Quellpaket. Die aktuelle
Pi-Version von labwc und `libwlroots-0.20` bleibt unverändert ausgewählt. Es gibt
keine erzwungene Herabstufung, keine feste Versionssperre und keine Ausnahme
von der vollständigen Quellprüfung. Die Präferenz wird nicht vom Installer auf
bestehenden Geräten eingerichtet. Ihr Verhalten folgt der vorhandenen
[APT-Paketauswahl](https://manpages.debian.org/trixie/apt/apt_preferences.5.en.html).

Die Release-Hinweise nennen die verbleibenden Funktionen und Prüfgrenzen.
Insbesondere entstehen dadurch keine angeblich abgeschlossenen Streaming-,
Windows-11-Pro- oder persönlichen Anbieterabnahmen. Modellanfragen bleiben
ausgeschlossen. Die eigentliche neue Streaming-Integration bleibt währenddessen
in ihrem gesonderten Entwicklungszweig und wird nicht ungeprüft in das Image
übernommen.
