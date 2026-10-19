# Designsystem

Verbindliche Referenzen: `assets/references/1000141105.png` (Dashboard) und
`1000141106.png` (Logo). Originale bleiben unverändert erhalten. Die Kopfzeile
zeigt einen Anschnitt des gelieferten Logos; der helle Rampi-Schriftzug ist
Systemtext, damit er auf dunklem Grund lesbar bleibt.

Designfläche 1600×900, proportional auf die Bildschirmgröße skaliert. Header
oben, sechs große Kacheln, Kanban links unten, vier Vorschaupanels rechts,
Systemleiste unten mit Einstellungen links. Keine Verläufe oder Schatten.

| Token | Wert |
|---|---|
| Hintergrund | #080f16 |
| Panel | #101c26 |
| Kanban | #ff3c61 |
| Codex | #087cf5 |
| Claude | #ffd53d |
| Antigravity | #15cbbb |
| Remote | #4934c8 |
| Browser | #1d3448 |
| Erfolg/Akzent | #19d6b2 |

Qt Quick Shapes verformt alle vier Kachelseiten in einer 200-ms-Sequenz.
Fokus ändert die Flächenfarbe statt eines zusätzlichen Rahmens. Bewegung kann
reduziert werden. Animation läuft ausschließlich beim Auswahlwechsel.
Die Hauptkacheln verwenden sechs festgelegte Lucide-SVG-Icons mit vollständigen
ISC-/Feather-MIT-Lizenzhinweisen. Es sind neutrale Modulicons; offizielle Anbieterlogos
werden nicht als selbst lizenzierte Grafiken ausgegeben. Eigenständige
SVG-/PNG-/Boot-/Login-Varianten sind noch zu erstellen und zu prüfen.
