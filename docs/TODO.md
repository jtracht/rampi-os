# Rampi OS: verbleibende Software-Abnahme

Stand: 2. November 2026. Belegt: **92/95 Punkte (96,8 %)**.
Die Liste wird mit tatsächlichen Ergebnissen aktualisiert. Lokale Komponenten-
prüfungen ersetzen weder die vollständige CI noch die Image-Abnahme.

- [x] UX-Korrekturen für Beschriftungen, lesbare Textauswahl und Cursorverhalten entwickeln.
- [x] Tatsächliche GTK-Oberfläche in Deutsch und Englisch prüfen und Screenshots erfassen.
- [x] Lokalen Bluetooth-HID-Komponentenlauf mit zwei Konten und sechs Layouts auswerten:
  30 Kernel-Eingabequittungen, Wiederverbindung, Maus, reservierter Wechsel und Entfernen.
- [x] 345 Python-Tests, Rust-Formatierung/Clippy und vollständigen Geheimnisscan bestehen.
- [x] Fehler der nativen PR-53-CI bestimmen: fehlendes Pillow im Host-Prüfprozess.
- [x] Gesamten Nachweisprüfer im vorhandenen SDK mit seiner installierten Bildbibliothek ausführen;
  identische Pflichtprüfungen beibehalten und vorhandene CI-Artefakte damit prüfen.
- [x] Heruntergeladene frische PAM-/HID-Nachweise beider Architekturen unabhängig prüfen.
- [x] Zweiten CI-Fehler auf AMD64 eingrenzen: virtueller Adapter beim Power-Aufruf noch nicht bereit.
- [x] Zustandsbasierte Bereitschaftsprüfung entwickeln; dauerhaften falschen Zustand
  und beendeten Emulator in Negativkontrollen ausdrücklich ablehnen.
- [x] Frische native CI für `00af710` auf AMD64 und ARM64 samt sechs Layouts und zwei PAM-Konten bestehen.
- [x] Heruntergeladene Nachweise für `00af710` unabhängig mit eingefrorenen Prüfern prüfen:
  beide Programme, PAM/HID/Funk und sieben Paketprüfsummen.
- [x] PR 53 als `523d3c8` zusammenführen; identischen geprüften Quellbaum bestätigen.
- [x] Allgemeine und native Push-CI für `523d3c8` bestehen.
- [x] Ersten lokalen Verbundlauf ausführen und den falschen Testklick mit gespeichertem Screenshot eingrenzen.
- [x] Globale GTK-Position 0/0 durch tatsächliche Fensterkoordinaten ersetzen;
  den Randfall mit vorhandenem Hostprofil im Deutsch-/Englisch-Test reproduzieren und korrigieren.
- [x] Weitere frische Verbundläufe auswerten; TLS-Kaltstart und Mausgerätewechsel eingrenzen.
- [x] Lokale Audiovorbereitung vor den RDP-Netzaufbau ziehen, TLS-Frist unverändert lassen;
  tatsächliche isolierte RDP-Kontrollprüfung erneut bestehen.
- [x] Verzögerte GTK-Cursoränderung nach Bluetooth-Tastatureingabe korrigieren;
  gezielter lokaler Bildvergleich: unsichtbar nach Tastatur, sichtbar nach Mausbewegung.
- [ ] Diese Cursorbilder anschließend im vollständigen frischen Verbundlauf bestätigen.
- [ ] Vollständigen Bluetooth→RDP-Verbundlauf nach den Korrekturen bestehen.
- [x] Den vollständigen frischen Verbundtest als Pflichtprüfung beider CI-Architekturen einbauen.
- [ ] Diese neuen CI-Läufe auf dem endgültigen Quellstand bestehen und unabhängig prüfen.
- [x] Abgeschotteten XRDP-Quittungsserver mit tatsächlichem RDP-Client prüfen:
  empfangene Zeichen, Dashboard-Rückkehr ohne manuelle Fokuskorrektur und Wiederverbindung.
- [ ] Bluetooth-Eingaben durch die normale integrierte RDP-Oberfläche bis zu einem
  isolierten Linux-XRDP-Testserver prüfen: Zeichen, Modifikatoren, Maus und Wiederverbindung.
- [ ] Serverseitig nachweisen, dass reservierte Rampi-Tastenkombinationen nicht weitergeleitet werden.
- [ ] Verbleibende UX-/Layoutprobleme aus vollständigen Bedienläufen korrigieren;
  unterstützte Bildschirmgrößen und Leistungsbudgets erneut anhand der Nachweise beurteilen.
- [ ] Endgültige Quellrevision, Programmdateien und alle heruntergeladenen Nachweise unabhängig zuordnen.
- [ ] Ausschließlich erfolgreich geprüfte Änderungen zusammenführen; integrierte Zweige bereinigen.
- [ ] Allgemeine und native Push-CI derselben endgültigen main-Revision bestehen.
- [ ] Frisches flashbares ARM64-Image bauen und tatsächliche grafische Anmeldung mit zwei Konten prüfen.
- [ ] Release mit Image, Installern, Windows-Paket, vollständigen Quellen, Lizenzen und Prüfsummen veröffentlichen.
- [ ] Veröffentlichte Dateien erneut herunterladen und Tag, Programme, Image, Quellen und Prüfsummen überprüfen.
- [ ] Erst nach vollständiger unveränderter Abnahmeskala 100 % erklären.

Windows-Komponenten werden ausschließlich in isolierter GitHub-CI geprüft.
Keine persönlichen oder externen Windows-Testhosts, Hardwaretests oder Modellanfragen.
Die veröffentlichten Dateien von v0.6.0-dev.6 bleiben unverändert.

Aktueller Zwischenstand: Deutsch und US haben den lokalen verbundenen RDP-Lauf
mit Maus, Dashboard-Rückkehr und Wiederverbindung bestanden. Beim britischen
Layout brach eine Oberflächenabfrage während der Wiederverbindung ab. Die
Abfrage liefert bei einem veralteten Objekt nun keine Daten und wird durch die
bestehenden Bereitschaftsprüfungen erneut gelesen. Der Negativtest besteht.
Das ist weiterhin keine vollständige frische Sechs-Layout-Abnahme.

Weitere Wiederholung: Der deutsche Cursor-Bildvergleich besteht auch mit der
Vorabversionskennung dev.7. Danach brach die Auswahl der RDP-Kachel an einem
veralteten Oberflächenobjekt ab. Nur lesende Steuerelementabfragen werden nun
kurz begrenzt erneut gelesen; Aktionen selbst werden nie wiederholt. Der
Negativtest für einen unsicheren Klick-Rückgabestatus und doppelte Treffer
sowie die beiden tatsächlichen Sprach-Kontrollläufe bestehen. Noch keine
frische vollständige Verbundabnahme.

- [x] Bluetooth-Bestätigung mit gewähltem Gerät/Adapter und eindeutiger
  Vertrauensaktion entwickeln; Beschriftung folgt dem tatsächlichen BlueZ-Zustand.
- [x] Den tatsächlichen GTK-/D-Bus-Lauf für Vertrauen, Entziehen und Abbrechen
  prüfen: Standardfokus auf Abbrechen, keine Zustandsänderung beim Abbrechen,
  genau ein Fenster.
- [ ] Diese Verbesserung zusätzlich im vollständigen frischen Eingabelauf abnehmen.

Die bisher längste lokale Wiederholung hat Deutsch, US, Britisch und Französisch
vollständig durchlaufen. Bei Spanisch endete der Prüfemulator an seiner alten
40-Minuten-Gesamtgrenze. Seine Gesamtgrenze entspricht jetzt den 6000 Sekunden
des erweiterten Verbundprüfers; einzelne Antwort-/Verbindungsfristen bleiben
unverändert. Der gesamte Sechs-Layout-Lauf ist weiterhin nicht abgenommen.

Weitere Eingrenzung: Ein erhaltener Ablaufstapel zeigt eine langsame Zustands-
abfrage innerhalb des Zugänglichkeitsbaums. Der Prüfhelfer hat jetzt pro
Lesedurchlauf ein eigenes Budget, besucht identische Objekte nur einmal und
verwirft bei unvollständiger Abfrage sämtliche Zeilen. Die Seitenprüfung
behält ihre bisherige Frist und übernimmt Wiederholungen; verschachtelte
50-fache Leseversuche entfallen. Kontrollierte Gegenprüfungen für Zyklen,
Teilinformationen, genau einen Leseversuch und nicht doppelt ausgelöste
Aktionen sowie beide tatsächlichen Sprachläufe bestehen. Die vollständige
frische Verbundabnahme dieses korrigierten Prüfhelfers steht noch aus.

Die ursprünglichen CI-Rohprotokolle von 64b9de0 sind erhalten: Beide
Architekturen erreichten nach den sechs Layouts die abschließende Entkopplung,
führten deren Bestätigung aber noch über eine alte Bildschirmposition aus.
Diese Bestätigung verwendet jetzt ebenfalls das eindeutige tatsächliche
Bedienelement. Zusätzlich übernimmt der Linux-Aufrufer nur den neu erzeugten
Testordner vom Root-Container, damit Serverbelege gesammelt und eigene Seeds
gelöscht werden können. Ein echter Linux-Dateisystemtest besteht; Verzeichnismodus
0755, private Dateimodi 0600 und fremde Zugriffsverweigerung bleiben erhalten.
Keiner dieser fehlgeschlagenen Läufe zählt als vollständige Abnahme.

Die neue Fünf-Sekunden-Einzelabfrage war im langsamen QEMU-Gast zu knapp:
Der Screenshot zeigt das gekoppelte Gerät mit verfügbarem Vertrauensknopf,
aber der Prüfer erhielt leere Daten. Eine einzelne vollständige Abfrage darf
nun bis zu 15 Sekunden beanspruchen, weiterhin innerhalb der bestehenden
60-Sekunden-Aufruf- und 90-Sekunden-Seitenfrist. Abfragedauer, Zeilenzahl und
freigegebener Fehlergrund werden ohne Feldinhalte protokolliert. Die
Gegenprüfungen und beide tatsächlichen Sprachläufe bestehen erneut. Ein
vollständiger frischer Nachweis bleibt erforderlich.
