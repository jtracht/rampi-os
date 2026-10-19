# Native KI-Terminals

Rampi überträgt ein interaktives OpenSSH-Terminal; VTE rendert die Anzeige.
Der Host startet `codex`, `claude` beziehungsweise `agy` in psmux 3.4.0.
WSL wird nicht benötigt. Anbieteranmeldung, Projektsicherheit und
Berechtigungsdialoge bleiben unverändert in den offiziellen CLIs.

Feste Windows-Sitzungen heißen rampi-codex, rampi-claude und rampi-antigravity.
`new-session -A` verbindet erneut mit einer bestehenden Sitzung. Ein SSH-Ausfall
soll nur den Client beenden, nicht den abgekoppelten ConPTY-Server. Lokal wurde
dies über unabhängige Clients geprüft; die vollständige SSH-/VPN-Unterbrechung
steht als eigener Abnahmetest aus. Bei Rückkehr erneut die Kachel öffnen.
Sitzungen gezielt beenden: Host-Adapter mit `-Module codex -Action Stop` aufrufen.
Den Server nicht pauschal mit kill-server beenden: Er könnte andere persönliche
Sitzungen verwalten. Ein Hostneustart muss Prozesse nicht erhalten.

Für ein anderes Projekt die vorhandene Anbietersitzung bewusst beenden und danach
mit neuem Projektprofil öffnen. Anbieterfunktionen zur Wiederaufnahme werden
innerhalb der offiziellen CLI verwendet; Rampi erfindet keine Resume-Flags.

Quellen (19.10.2026):
- https://github.com/openai/codex
- https://code.claude.com/docs/en/setup
- https://www.antigravity.google/docs/cli/install/ (`agy`, native Windows-Unterstützung)
- https://github.com/psmux/psmux (ConPTY, SSH, serverseitige Persistenz, MIT)
