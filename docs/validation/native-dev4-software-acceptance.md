# Software-Abnahme des nativen dev4-Releases

## Zugeordnete Quellen und tatsächliche Dateien

- Öffentliche Vorabversion: [v0.6.0-dev.4](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.4).
- Unveränderter Release-Quellstand: `f0490436d5cadd630f1b5f1487fb470312837d4b`.
- Allgemeine/native Push-CI: `40755459518` / `40755459467`, beide erfolgreich.
- Frischer Image-/Release-Lauf: `40766112011`.
- Öffentlich heruntergeladene und vollständig geprüfte Dateien: 28.
- Image: `image_2026-10-28-rampi-os-rpi3bplus-v0.6.0-dev.4.img.xz`.
- Image-SHA256: `032b253c88e9d722ea33dab46e999744d65ab4f12155459fe5b45723f72c2b6c`.
- Tatsächlich installiertes Release-Programm: `d826c2f3bb027de4acfb0a5033a7df31f85f7d86f499b45150b692d095178468`.

Die unabhängige Prüfung verwendet die unveränderten, eingefrorenen Prüfer des
Release-Quellstands. Sie kontrolliert alle SHA256SUMS, vorhandene GitHub-Digests,
Tagrevision, Quellarchive, Paket-/Programmzuordnung, Lizenzen und grafische Belege.
CI-Programme im Debug-Profil sind nicht mit dem Release-ELF gleichzusetzen:
ihre eigenen Hashes stehen in den jeweiligen nativen Nachweisen.

## Fünf abgeschlossene Softwarebereiche

| Bereich | Zusätzlicher Abschlussnachweis |
|---|---|
| Einrichtung | Zwölf erreichbare Stationen, Tastaturbedienung, Fortsetzen alter IDs, übersetzte DE-/EN-Validierung, echte persönliche glibc-Locale nach PAM und erneuter Anmeldung; beide originalen Erstkonto-Verfahren mit normalen Neustarts im frischen Image |
| VPN | Reale WireGuard-Peers über NetworkManager mit privaten Profilen; privates Tailscale mit Kernelverkehr, Rechteverweigerung und Wiederverbindung; tatsächliche signierte manuelle Installation des vorhandenen Vendor-Dienstes und unveränderte Dateien/Prozess-ID beim Wiederholen |
| RDP/Streaming | Tatsächliche eingebettete TLS-/NLA-Anmeldung einschließlich falscher Konten, Domain und Kennwörter; Frames, Maus, Scrollen, Unicode-Zwischenablage und Wiederverbindung; Sunshine-Kopplung, abgewiesener falscher Schlüssel, private Identität, Bild/Ton und quittierte Eingabepakete über zwei Verbindungen und 600 Sekunden Dauerlast |
| Kanban | Vorhandene sechs Anbieter und JSON, HTTPS-/Secret-Service-Verträge; tatsächliches Gitea mit privaten Repository-, Organisations- und Benutzerprojekten, Filtern, Aktualisierung und privatem Offline-Cache |
| Sicherheit/Isolation | Zwei echte Linux-/PAM-Konten auf beiden Architekturen, falsches Kennwort verweigert, private Dateien/SSH-Agenten/Busse/Schlüsselbünde und erneute Entsperrung; TLS-, Archiv-, Rechte- und Erhaltungsprüfungen sowie unveränderte Programmdateien im frischen Image |

Die virtuelle Abnahme benutzt vorhandene Dienste, Protokolle und Bibliotheken.
Sie ist keine Bestätigung physischer Geräte, externer Cloudkonten oder eines
Windows-Testhosts. Sunshine-Eingaben werden am tatsächlichen Serverprotokoll
quittiert; dessen Plattform-Injektion bleibt im Test deaktiviert.

Der kalte persönliche Sprachabruf wird mit einer begrenzten Frist von 30 Sekunden
ausgeführt. Die frühere Dreisekundenfrist scheiterte tatsächlich im kalten Gast;
ein wiederverwendeter Diagnosegast ersetzt keine der frischen Abnahmen hier.

## Unveränderte Bewertung und verbleibende Grenzen

Fünf Bereiche steigen nach ihrer vollständigen Softwareabnahme von 4 auf 5.
Damit gilt **86/95 → 91/95 = 95,8 %**; der Nenner bleibt 19 Bereiche zu je 5 Punkten.
Testanzahl und Wartezeit ergeben keine Punkte. Die entfernten KI-Anbindungen
bleiben entfernt und bringen keine umverteilten Punkte.

Tastatur-/Layout-Randfälle, durchgängiges Bluetooth-HID, tatsächliche Windows-
Host-Randfälle und weiterer Fokus-/Bedienungsfeinschliff behalten jeweils 4/5.
Das Gesamtprodukt wird deshalb weiterhin ausdrücklich als Vorabversion geführt.
`regular_release` bleibt `false`; ein vollständiger 100-Prozent-Abschluss wird
nicht behauptet. Hardwaretests, Windows-Testhosts und Modellanfragen bleiben
wie beauftragt ausgeschlossen.
