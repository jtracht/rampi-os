# Abschlussplan: die letzten drei Softwarepunkte

Stand 3. November 2026: **92/95 = 96,8 %**. Die Skala bleibt unverändert.
Diese Planung ist keine Abnahme und kein Veröffentlichungserfolg.

## Konkreter Ausgangspunkt

Der gemeinsame native Lauf `41545087516` für PR 54, Kopf
`4ca1743533985bbe5c83303ab99a2e2650e13a05`, hat auf ARM64 bestanden.
AMD64 scheiterte nach tatsächlicher Kernel-Eingabe beim Warten auf ein
Zeichen im isolierten RDP-Quittungsserver. Das ist zunächst eine fehlgeschlagene
Ende-zu-Ende-Prüfung, keine bewiesene Produkt- oder Infrastrukturursache.
Die automatische Zusammenführung/Veröffentlichung ist deshalb gestoppt.
Beide Architekturen müssen auf demselben endgültigen Kopf bestehen.

## Abnahmematrix

| Noch offener Punkt | Erforderlicher positiver Nachweis | Fehler, die ausdrücklich abgewiesen werden müssen |
|---|---|---|
| Tastatur/Maus: 4 → 5 | Zwei PAM-Konten, alle sechs vorhandenen Layouts; echte Bluetooth-HID-Berichte → Kernel → normale Rampi-Oberfläche → unabhängige RDP-Serverquittungen; Maus, Modulrückkehr ohne Fokusreparatur und Wiederverbindung | Falsches Zeichen/Modifikator, fehlendes Loslassen, doppelte Eingabe, reservierter Home-Wechsel auf dem Server, fremdes Profil |
| Bluetooth: 4 → 5 | Entdecken, Koppeln, Vertrauen/Entziehen/Abbrechen, tatsächliche HID-Verbindung, Wiederverbindung und Entfernen des Bonds samt Eingabegerät | Abbrechen verändert Zustand, falsches Gerät betroffen, Gerät trotz Entfernen verbunden, fremde private Daten lesbar |
| Design/Bedienung: 4 → 5 | Tatsächliche deutsche/englische Seiten und Fokuswege, genau ein Fenster, eindeutiger Gerätekontext, Standardfokus Abbrechen; Cursor nach Tastatur verborgen und nach Mausbewegung sichtbar | Staler Cursor, uneindeutige Bestätigung, unsichtbarer Fokus, zusätzliche Fenster, unlesbare oder fehlende Texte |

Punkte erst nach integrierter Quelle und zugeordneten Nachweisen vergeben.
Die bestehende Animations-/Rendering-Abnahme bleibt erforderlich; diese neuen
Tests allein behaupten weder Animationsqualität noch vollständige Bedienbarkeit.

## Schnellster Prüfweg ohne geringere Anforderungen

1. **Schnelle Fehlerkontrollen vor dem Push.** `python -m pytest
   tests/test_hid_accessibility_guards.py -q` prüft den tatsächlichen
   Testhelfer mit kontrollierten externen AT-SPI-Antworten. Dazu kommen
   `python -m pytest -q`, Ruff sowie Rust-Formatierung/Clippy.
   Die neuen Kontrollen laufen durch die vorhandene pytest-Erkennung bereits
   automatisch in der allgemeinen Linux-/Windows-CI; kein neuer Dienst nötig.
2. **Echte kurze Oberflächenläufe.** Vorhandene SDK-Tests
   `tests/rust/test-accessibility.py`, `test-bluetooth.py` und `test-rdp.py`
   weiterverwenden: echte GTK-/D-Bus-/RDP-Komponenten, Sprachbilder und Fokus.
   Diese Komponentenprüfungen ersetzen den folgenden Verbundlauf nicht.
3. **Den aktuellen AMD64-Fehler zuerst lokalisieren.** Die letzte lokale
   Taste und ihr Kernelintervall mit dem unabhängigen Servertranskript,
   Serverereignissen, Verbindungszustand und Fehlerbild abgleichen. Fehlende
   Eingabe von falschem Layout oder verlorenem Fokus unterscheiden. Erst die
   belegte Ursache korrigieren; keine pauschale Wiederholung oder längere Frist.
   Vorhandene ARM64-Nachweise als Vergleich verwenden, nicht als AMD64-Ersatz.
4. **Ein vollständiger frischer Lauf pro endgültigem Kopf.** Vorhandenen
   `scripts/test-hid-rdp.py` auf AMD64 und ARM64 benutzen. Unabhängige
   Serverquittungen und `check-hid-rdp-evidence.py` bleiben Pflicht. Entwicklungsgäste
   dürfen Ursachen eingrenzen, zählen aber niemals als frische Abnahme.
5. **Nach erfolgreicher unabhängiger PR-Prüfung zusammenführen.** Identischen
   Quellbaum bestätigen. Beide Push-CIs der tatsächlichen Main-Revision bestehen
   und heruntergeladene Programm-/Paket-/Login-/HID-Nachweise erneut prüfen.
6. **Genau ein frischer Image-/Release-Lauf.** pi-gen, Boot, grafische Anmeldung
   zweier Konten, unveränderte Programme und vollständige Drittanbieterquellen.
   Danach veröffentlichte Dateien erneut herunterladen: Tagrevision,
   Vorabversionsstatus, Image, Installer, Windows-Paket, Quellen, Lizenzen und
   sämtliche Prüfsummen/Server-Digests verifizieren.

Zeit sparen durch diese Reihenfolge und Wiederverwendung vorhandener Werkzeuge,
nicht durch das Überspringen eines fehlgeschlagenen Nachweises. Für einen
unveränderten laufenden Kopf keinen zweiten Dispatcher starten. Nach einem
echten Fehler dessen Prozess als beendet behandeln und erst nach Diagnose eine
neue Revision prüfen. Eine feste Abschlusszeit wäre ohne grüne Verbundabnahme
nicht belastbar.

## Neue automatische Regressionstests

`tests/test_hid_accessibility_guards.py` prüft:

- Zyklen und doppelte Objektverweise ohne Mehrfachdurchlauf;
- vollständiges Verwerfen von Teilresultaten bei Zeitablauf, stalen Objekten
  und zu tiefen Bäumen;
- begrenzte Wiederholung ausschließlich lesender Abfragen;
- keine erneute Aktion nach unsicherer Bestätigung oder negativer Antwort;
- keine Aktion bei doppelten oder nicht bedienbaren Schaltflächen;
- tatsächlichen Fensterkoordinaten-Modus und Zurückweisung ungültiger Rechtecke;
- genau eine CLI-Lesung und erforderliche aktuelle Rampi-Seite.

Diese kontrollierten Negativfälle liefen bisher nur als lokale Diagnose.
Sie werden jetzt dauerhaft vor den teuren End-to-End-Läufen ausgeführt.
Die externen Framework-Antworten sind hier Testdoubles; ein positives Ergebnis
ist ausdrücklich **kein** GTK-, Bluetooth-, RDP- oder Image-Abnahmenachweis.

## Grenzen

Keine Hardwaretests, persönlichen Rechner, externen Windows-Testhosts,
Modellanfragen oder direkten KI-Integrationen. Isolierte Windows-GitHub-CI bleibt
der vereinbarte Windows-Prüfweg. Keine neuen App-Aufgaben oder Automationen.
Das Produkt bleibt bis zur tatsächlichen vollständigen Abnahme unvollständig.

## Umgesetzte nächste Schritte

Zusätzlich zu den 16 Helfer-Gegenprüfungen bestehen jetzt 14 unabhängige
Serverquittungs-/Bereitschaftskontrollen (`tests/test_hid_server_receipts.py`).
Der normale RDP-Verbundtest wartet auf tatsächliches Mapping und beobachteten
Startfokus des Remote-Testprogramms. Das vermeidet ein nachweislich fehlendes
Bereitschaftskriterium; die Erklärung des alten AMD64-Ausfalls bleibt bis zur
frischen Wiederholungsabnahme eine Hypothese. Der Beobachter repariert keinen Fokus.

Der Quittungsexport verwendet sichtbare Dateinamen; so bleiben Dateien nach dem
regulären GitHub-Artefakt-Upload verfügbar. Es werden keine beliebigen versteckten
Dateien freigegeben. Alle Quittungen werden auf Fixture-Kennwort-Lecks geprüft.
Der unabhängige Prüfer verlangt den zusätzlichen Bereitschaftsbeleg mit passender
Serverkennung. Bestehende veröffentlichte Releases bleiben unverändert.

Die gemeinsame Oberfläche erhält Fokusflächen für Eingabefelder, passende
Mauszeiger, getrennte Erfolgs-/Fehlerfarben und eine klare Bestätigungsfläche.
Erledigte Rückmeldungen verlassen ihren Seitenkontext; Fehler werden nicht
ungefragt entfernt. Der tatsächliche Deutsch-/Englisch-Test prüft Speichern,
Rückkehr und sichtbare Rückmeldung innerhalb der Bildschirmgrenzen.
375 Python-Tests und die vorhandenen Rust-/GTK-/RDP-Komponentenprüfungen bestehen
lokal. Frische CI und Image-Abnahme dieser Revision bleiben Pflicht.
