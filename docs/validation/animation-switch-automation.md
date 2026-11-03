# Animationen, Icons und Schiebeschalter

Stand: 3. November 2026. Der gemeldete Raspberry-Pi-Ruckler ist der Anlass dieser
Änderung. Die folgenden Messungen stammen aus Softwaretests, nicht aus einer
neuen Messung auf dem Raspberry Pi. Der belegte Gesamtstand bleibt 96,8 %.

## Umgesetzte Optimierung

Zuvor behielt jeder Liquid-Button einen permanenten GTK-Frame-Callback. Auch im
Ruhezustand wurden dabei Zustände und Animationseinstellungen abgefragt. Eine
aktive Fläche wurde ohne eigene Obergrenze bei jedem Frame neu gezeichnet.

Jetzt registriert nur eine tatsächlich bewegte Fläche einen Callback. Nach dem
Impuls, bei reduzierter Bewegung oder auf einer nicht gemappten Seite wird die
Arbeit beendet. Die Neuzeichnung einer aktiven Softwarefläche ist auf nominal
30 Bilder/s begrenzt. Statische Knopfflächen verwenden vorhandene GTK/GSK-
Rundrechtecke; Cairo bleibt für die ungleichmäßige Wellenkontur zuständig.
Reine Backend-/Empfindlichkeitsänderungen lösen keinen neuen Wellenimpuls aus.
Die Welle an allen vier Kanten bleibt erhalten. Display- und Treibereinstellungen
werden nicht geändert.

## Einheitliche Bedienelemente

„Bewegung reduzieren“, Klickklänge, WLAN und Bluetooth verwenden native GTK-
Schiebeschalter. Ein ist grün mit dem Schieber rechts; Aus ist grau mit dem
Schieber links. Der Zustand ist zusätzlich für assistive Technik verfügbar.
Bluetooth ändert erst nach Bestätigung die tatsächliche BlueZ-Einstellung;
Abbrechen erhält den ursprünglichen Zustand. Ohne Adapter bleibt der Schalter
deaktiviert. Checkboxen zur ausdrücklichen Zustimmung bleiben Checkboxen.

Navigation und Systemschalter verwenden mitgelieferte Lucide-SVGs. Die beiden
zusätzlichen Icons stammen vom bereits festgelegten Commit; vorhandene
Lizenzhinweise bleiben erhalten. Fehlende Bilddateien dürfen im Test nicht
unbemerkt durch ein Platzhaltersymbol ersetzt werden. Zusätzliche leere
Fokusstationen um Bluetooth-Aktionen wurden entfernt.

## Automatisch geprüfte Eigenschaften

| Eigenschaft | Tatsächlicher automatischer Nachweis |
|---|---|
| Keine ruhenden Animationstakte | GTK-Callbackzähler bleibt im Ruhezustand unverändert |
| Reduzierte Bewegung | Callbackzähler bleibt auch bei fokussierter Fläche unverändert |
| Begrenzte aktive Neuzeichnung | Paintzähler wird gegen die tatsächlich gemessene Beobachtungsdauer geprüft |
| Asymmetrische Welle | Bestehender Vergleich der tatsächlich gerenderten Konturen an allen vier Kanten |
| Native Schalter | Tastatur-Tab/Leertaste, tatsächlicher Checked-Zustand, On-/Off-Pixel und sichtbare Grenzen in Deutsch/Englisch |
| Bluetooth-Leistung und Abbrechen | Produktionsadapter gegen privaten BlueZ-D-Bus; Bestätigung, Zustandserhalt und tatsächliche Property-Änderung |
| Icons | Tatsächliche GTK-Bilder müssen aus geladenen Paintables bestehen, nicht aus Fallback-Symbolen |
| Tastaturnavigation | Eingaben erst bei tatsächlich aktivem Fenster und fokussierter erster Kachel; tatsächlicher Hin-/Rückweg statt fester Schlafzeiten |
| Dokumentationsbilder | Export erst nach Programm-, Sprach-, Pixel- und Animationsprüfung; PNG-Validierung, unveränderte Bytes, SHA-256, Galerie und ZIP |

`check-native-evidence.py` verlangt die zusätzlichen Animations- und
Schalternachweise auf beiden Architekturen. Gegenprüfungen lehnen falsche
Programme, fehlende Zustände, überschrittene Budgets, ungültige Messwerte,
beschnittene Schalter und widersprüchliche On-/Off-Bilder ab. Der Export
überschreibt keine vorhandenen Verzeichnisse oder ZIP-Dateien und übernimmt
keine nicht zum Programm passenden RDP-Bilder.

## Reproduzierbarer Ablauf

Der vorhandene native Wayland-Lauf führt die neuen Prüfungen aus und erzeugt
anschließend mit `scripts/export-ux-docs.py` automatisch `ux-docs/` und
`ux-docs.zip` im Aufnahmeverzeichnis. Es werden keine UI-Bilder erzeugt oder
retuschiert; ausschließlich tatsächliche Aufnahmen werden unverändert kopiert.

Ein zusätzlicher Export einschließlich des separat geprüften RDP-Clients:

```text
python scripts/export-ux-docs.py --captures <Wayland-Aufnahmen> --rdp <RDP-Aufnahmen> --output <neues-Ziel> --expected-binary <SHA256-des-ausgeführten-ELF>
```

Ein früher lokaler Lauf hat bereits 0 ruhende und 0 reduzierte Callbacks sowie
18 Neuzeichnungsanforderungen in 600,15 ms gemessen. Gezählt werden Aufrufe von `queue_draw()`, nicht physisch dargestellte Frames.
Die JSON-Nachweise enthalten die
Prüfsumme des tatsächlich ausgeführten Programms und weisen den virtuellen
Messumfang ausdrücklich aus. Erst die endgültigen CI-/Image-Nachweise dürfen
für die Release-Abnahme verwendet werden. Subjektives Bewegungsgefühl und echte
Pi-Frametimes werden durch diese Softwaremessung nicht behauptet.
