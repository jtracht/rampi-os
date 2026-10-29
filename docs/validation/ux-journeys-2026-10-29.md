# UX-Prüfung vom 29. Oktober 2026

Gesamtstand unverändert: 91/95 Punkte (95,8 %). Diese lokalen Bediennachweise
ersetzen weder die abschließende CI beider Architekturen noch einen frischen
Release-Image-Test.

## Ausführung

Die tatsächliche Rust/GTK-Anwendung läuft unter labwc/Wayland im isolierten
Container. wtype und wlrctl liefern Tastatur- und Mausereignisse; grim nimmt
die tatsächlich gerenderten Ansichten auf. Keine nachgebauten Screenshot-Mockups.
Auflösungen: 1280×720, 1600×900 und 1920×1080.

Geprüfte Bedienwege:

- Dashboard: Start, Hover, Pfeiltasten, Enter, Cursorwechsel und reduzierte Bewegung.
- Einstellungen: Kategorien öffnen, am Listenende umlaufen, von Maus auf Tastatur
  wechseln, Detailseiten öffnen und mit Escape zur vorherigen Auswahl zurückkehren.
- Hostprofil: Felder mit Tab erreichen, Werte eingeben und Profil speichern.
- WLAN/Bluetooth ohne Auswahl: ungeeignete Aktionen bleiben deaktiviert.
- Terminal: Escape erreicht das Terminal; Strg+Alt+Home kehrt zum Dashboard zurück
  und wird nicht an das untergeordnete Terminal weitergegeben.
- Genau ein Anwendungsfenster bleibt geöffnet.

## Gefundene und korrigierte Probleme

1. Maus und Tastatur konnten zwei Kategorien gleichzeitig hervorheben.
   Tatsächliche Mausbewegung übernimmt nun den gemeinsamen Fokus; nach einem
   Tastaturwechsel bleibt nur die aktuelle Kategorie ausgewählt.
2. Dashboard-Kacheln bekamen zusätzlich zur eigenen Wellenfläche eine zweite
   graue Oberfläche und zusätzliche Abstände. Sie verwenden wieder ihren
   vorhandenen eigenen Renderer mit den nativen GTK-Button-Aktionen.
3. WLAN- und Bluetooth-Aktionen waren ohne ausgewähltes Netzwerk, Gerät oder
   Adapter bedienbar und wirkten ohne Ergebnis. Die betreffenden Aktionen werden
   jetzt erst durch eine passende Auswahl aktiviert.
4. Eine fehlende Systembus-Verbindung erschien als englischer Rohfehler.
   Die Oberfläche zeigt nun einen übersetzten Hinweis mit Verweis auf Diagnose;
   die ursprüngliche Fehlerursache bleibt für die Diagnose erhalten.
5. Detailseiten-Screenshots wurden mitten im animierten Seitenwechsel aufgenommen.
   Der Prüfer wartet nun auf das tatsächliche Ende der GTK-Transition, ohne die
   Animation der Anwendung abzuschalten.

## Nachweise und Grenzen

Lokale Originale: `artifacts/ux-journeys-selection-final/`, zugehöriges Protokoll:
`artifacts/ux-journeys-selection-final.log`. Frühere fehlgeschlagene Aufnahmen
bleiben erhalten. `tests/rust/check-visual.py` prüft die vier bewegten Kanten,
ruhende Konturen bei reduzierter Bewegung, einzelne Kategorieauswahl sowie
fehlende zusätzliche Kachel-Hintergründe anhand der echten PNG-Dateien.

Die Bluetooth-D-Bus-Prüfungen verwenden einen privaten Fixture-Bus. Sie prüfen
Bedienung, Adapterzuordnung und Discovery-Aufräumen, keine physische Funkstrecke.
Im lokalen Screenshot-Container fehlt ein Audiogerät; dessen Audiohinweis ist
kein bestandener Klangtest. Persönliche Rechner und Hardware wurden nicht benutzt.
