# Windows-Softwareabnahme des veröffentlichten dev6-Releases

Der Nutzer hat isolierte Windows-Komponentenprüfungen in GitHub-CI als
Abnahmeweg bestätigt. Persönliche Rechner, externe Windows-Testhosts und
Hardwaretests bleiben ausgeschlossen. Diese Abnahme bestätigt den vereinbarten
Softwareumfang; sie zertifiziert keinen physischen Windows-11-Pro-Rechner.

## Durchgängige Zuordnung

- Quelle: `3ae8c2db84eb2f7b96fc87bf9bd75b17bb466d79`.
- Tatsächliche Windows-Komponenten: [CI 40870427869](https://github.com/jtracht/rampi-os/actions/runs/40870427869).
- Endgültige allgemeine/native main-CI: `40880569312` / `40880569440`.
- Frischer Image-/Release-Lauf: `40892544298`.
- Öffentlich veröffentlichte und unabhängig heruntergeladene Vorabversion:
  [v0.6.0-dev.6](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.6).
- Tatsächliches Windows-Paket: `rampi-windows-host-0.6.0-dev.6.zip`.
- Paket-SHA256: `fc27dff313dcdd6e1f0b29fde456400880cd86115acad88219994ed3cf85c998`.
- Getesteter und im veröffentlichten ZIP enthaltener Installer-SHA256:
  `a9190468edcbed8a47ce68a6ccc977d4389a74b2cf4b65899a30b2dfb77d39ca`.

Die unabhängige Nachprüfung verwendet die eingefrorenen Prüfer und Testskripte
jener exakten Quelle. Sie kontrolliert erneut deren Git-Dateien, die Prüfsumme des
wirklichen Windows-Ergebnisses und die Installer-Datei im heruntergeladenen ZIP.
Die öffentliche Gesamtprüfung umfasst alle 28 Dateien, GitHub-Digests,
Quellarchive, Lizenzen und die tatsächliche grafische Image-Anmeldung.
Lokaler Zuordnungsnachweis: `artifacts/windows-dev6-area-accepted.json`.

## Abgenommener Softwareumfang

Der offizielle OpenSSH-Dienst läuft und prüft seine echte Konfiguration.
Wiederholte Installation erhält die vorhandenen Konfigurationsbytes; WhatIf
ändert die RDP-Einstellungen nicht. RDP benötigt NLA und die eingerichtete
Firewall-Freigabe gilt nur für private Netze. Die normale Installation weist die
nicht unterstützte Server-Edition zurück; nur der ausdrücklich aktivierte
Diagnoseschalter erlaubt die Komponentenprüfung im isolierten Server-Runner.

Zwei echte nichtadministrative Windows-Konten verwenden getrennte Profile,
Dateien und SSH-Schlüssel. Beide SSH-Anmeldungen liefern den jeweiligen SID;
der fremde Schlüssel und fremde private Dateien werden abgewiesen. Microsofts
vorhandener RDP-Client weist die echte erfolgreiche Anmeldung und den passenden
serverseitigen RemoteInteractive-SID nach. Ein falsches Kennwort erzeugt einen
wirklichen Security-Eintrag 4625 mit Status `0xc000006d` und Unterstatus
`0xc000006a`; ein bloßer Client-Timeout gilt nicht als Ablehnung. Zertifikats-
und CredSSP-Prüfungen bleiben aktiv. Testkonten und eigene temporäre Änderungen
werden im wegwerfbaren Runner entfernt; persönliche Rechner werden nicht benutzt.

## Bewertung

Die bislang offene Zuordnung zwischen Windows-Komponententest, endgültiger
Quelle und wirklich veröffentlichtem Hostpaket ist nun vollständig geprüft.
Der Bereich Windows-Host steigt deshalb im vereinbarten Softwareumfang von
4 auf 5 Punkte: **91/95 → 92/95 = 96,8 %**. Die Skala bleibt unverändert.
Bluetooth-HID, Tastatur-/Layout-Randfälle und die abschließende UX-Abnahme
bleiben jeweils bei 4/5. Das Gesamtprodukt ist weiterhin eine Vorabversion;
`regular_release` und vollständige Produktabnahme bleiben `false`.
