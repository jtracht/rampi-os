# Persönliche Tastaturkonfiguration: einheitliche Auswertung

Unveröffentlichter Folgestand nach dev4; noch keine neue Image-Abnahme oder
zusätzlicher Fortschrittspunkt. Der belegte Gesamtstand bleibt 91/95 = 95,8 %.

Die frühere RDP-Auswertung nahm den ersten exakt geschriebenen Layout-Eintrag
und begrenzte die Datei auf 16 KiB. Die Einstellungsseite wählte ebenfalls den
ersten passenden Listeneintrag. Dagegen verarbeitet der vorhandene
[labwc-Compositor](https://github.com/labwc/labwc/blob/master/src/config/session.c)
die Zuweisungen nacheinander, entfernt äußere Leerzeichen und überschreibt frühere
Werte. Bei vorhandenen doppelten Einträgen konnten deshalb Anzeige, Belegung
und RDP-Kennung auseinanderlaufen.

Der Rust-Adapter verwendet nun dieselbe begrenzte, eigentümergeprüfte Datei für
beide Oberflächenpfade. Der letzte wörtliche Eintrag entscheidet. Unbekannte,
leere oder dynamische eigene Belegungen werden nicht als frühere unterstützte
Belegung dargestellt. Rampi führt keine Variablen oder Shell-Eingaben aus.
Eine eigene Belegung bleibt unverändert, bis der Benutzer ausdrücklich eine
unterstützte Belegung zum Ersetzen auswählt. Fremde Einstellungen und Kommentare
bleiben beim Speichern erhalten; sämtliche alten Layout-Zuweisungen werden
durch genau eine neue ersetzt. Die übrigen XKB-Einstellungen werden erhalten.

Lokale Komponentenprüfung im vorhandenen isolierten Docker-/Wayland-SDK:

- 23 Rust-Core-Tests, Formatierung, Clippy und nativer Build bestanden.
- Ein echter gestarteter labwc liest zunächst Deutsch und danach einen mit
  Leerzeichen geschriebenen US-Eintrag. Sein tatsächlich gestartetes `printenv`
  bestätigt US, unabhängig vom Rust-Parser.
- Der tatsächliche GTK-Code zeigt dazu den US-Listeneintrag; die RDP-Funktion
  liefert `0x0409`, auch bei einer persönlichen Datei über 16 KiB.
- Eigene unbekannte Belegung bleibt unverändert und ohne falsche Listenauswahl.
  Reguläres Anwenden, Dateirechte, Erhaltung fremder Einträge, Symlink-Abweisung
  und die bestehende Bildschirm-Rücknahmeprüfung bestehen weiterhin.

Das prüft die Dateiauswertung, nicht sämtliche physische Tastatur-/HID-Eingaben,
externe `environment.d`-Übersteuerungen oder Shell-Variablenauflösung. Deshalb
bleibt der Tastaturbereich bei 4/5. Endgültige AMD64-/ARM64-CI und ein frischer
Release-/Image-Nachweis für den neuen Quellstand stehen noch aus.
