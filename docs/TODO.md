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
- [ ] Frische native CI auf AMD64 und ARM64 samt sechs Layouts und zwei PAM-Konten bestehen.
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
