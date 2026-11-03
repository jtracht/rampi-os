# Noch offene Punkte

Stand: 3. November 2026. **92/95 Punkte = 96,8 %**.
Momentaufnahme für Kandidat `8a23b9e` (PR 54), kein Abschlussnachweis.
Die allgemeine CI `41591450648` besteht; native CI `41591450680` läuft noch.

## Die drei noch nicht vollständig abgenommenen Produktbereiche

- [ ] **Tastatur und Maus:** alle sechs Layouts, zwei Konten, Cursorwechsel,
  tatsächliche Eingabe bis zum RDP-Server, Modulrückkehr und Wiederverbindung
  am endgültigen Quellstand auf AMD64 und ARM64 bestätigen.
- [ ] **Bluetooth:** Koppeln, Vertrauen/Entziehen, Abbrechen, HID-Eingabe,
  Wiederverbindung und Entfernen des Bonds samt Eingabegerät im vollständigen
  frischen Verbundlauf abschließen.
- [ ] **UX/Design:** endgültige Fokus-, Navigations-, Animations- und
  Rückmeldungsprüfungen mit den beiden Architekturen und dem Image verbinden.
  Lokale Deutsch-/Englisch- und vollständige Wayland-Bedienläufe bestehen bereits.

## Noch nötige Schritte bis zur Veröffentlichung

- [ ] Den alten AMD64-Zeichenquittungsfehler am korrigierten Kandidaten prüfen:
  das Testprogramm muss tatsächlich sichtbar und fokussiert sein. Falls der
  Fehler bleibt, die jetzt vollständig exportierten Serverbelege auswerten.
- [ ] Beide nativen CI-Läufe bestehen und heruntergeladene Nachweise unabhängig
  gegen Programmdateien, Paketprüfsummen und eingefrorenen Quellstand prüfen.
- [ ] Nur den unveränderten grünen PR-Kopf zusammenführen; danach beide
  Main-Prüfungen derselben endgültigen Revision bestehen und kontrollieren.
- [ ] Frisches ARM64-Systemimage bauen: Boot, grafische Anmeldung zweier Konten,
  falsches Kennwort, private Profile, unveränderte Programme und vollständige
  Drittanbieterquellen prüfen.
- [ ] Release veröffentlichen und die wirklich veröffentlichten Dateien erneut
  herunterladen: Image, Linux-/Windows-Pakete, setup.sh/setup.ps1, Quellen,
  Lizenzen, Tagrevision und sämtliche Prüfsummen/Server-Digests bestätigen.
- [ ] Erst danach den belegten Punktestand und einen möglichen vollständigen
  Softwareabschluss bewerten. Keine Hochrechnung allein aus Testanzahlen.
- [ ] Diese Screenshot-Dokumentation nach der laufenden Release-Abnahme in
  main übernehmen und den sichtbaren Versionsstand abgleichen.

## Bereits erledigt

- [x] Gemeinsame Fokus-/Cursor-/Rückmeldungs- und Bestätigungsverbesserungen gepusht.
- [x] 375 lokale Python-Tests bestanden, 12 übersprungen; Rust-Build, fmt, Clippy
  und Ruff bestanden.
- [x] Tatsächliche Deutsch-/Englisch-Oberfläche, gesamte native Wayland-Bedienung
  und isolierte RDP-Kontrolle einschließlich Eingaben, Maus und Zwischenablage bestanden.
- [x] Zehn unveränderte echte [Doku-Screenshots](SCREENSHOTS.de.md) samt Herkunft
  und Prüfsummen bereitgestellt.

Hardwaretests, persönliche Rechner, externe Windows-Testhosts und Modellanfragen
bleiben ausgeschlossen. Windows-Komponenten werden ausschließlich in der
vereinbarten isolierten GitHub-CI geprüft.
