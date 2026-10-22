# Rust-Tailscale-Statusabnahme vom 23. Oktober 2026

Entwicklungszweig: `codex/software-acceptance-85`. Lokal auf amd64 bestanden;
aktuelle CI-Artefakte werden separat geprüft. Dies ist keine vollständige
Tailscale-VPN-Abnahme und kein Nachweis einer persönlichen Kontoanmeldung.

Die produktive Rust-Anwendung erkennt die installierte offizielle Tailscale-CLI
und liest ihren Zustand mit `tailscale status --json --peers=false`. GIO startet
den Prozess ohne Shell und liest die Ausgabe asynchron. Nach fünf Sekunden oder
mehr als 256 KiB wird der Prozess beendet und eingesammelt. Fehlerdiagnosen
geben keine rohe CLI-Ausgabe oder Anmelde-URL weiter. Es werden keine bestehenden
Profile, Routing-Vorgaben oder Dienstkonfigurationen durch die Statusabfrage geändert.

Die Zustände `NeedsLogin`, `NeedsMachineAuth`, `Stopped`, `Starting`, `NoState`
und `Running` werden unterschieden. „Verbunden“ setzt außerdem eine positive
`Self.Online`-Angabe und mindestens eine gültige VPN-Adresse voraus. Unbekannte
Zustände und unvollständige Angaben werden nicht als verbunden ausgewiesen.
Die Statusanzeige und ihre Aktualisierung liegen direkt in der VPN-Seite.

Die Semantik folgt der [offiziellen CLI-Dokumentation](https://tailscale.com/docs/reference/tailscale-cli),
dem [offiziellen Statusbefehl](https://github.com/tailscale/tailscale/blob/v1.104.2/cmd/tailscale/cli/status.go)
und seinem [Statusschema](https://github.com/tailscale/tailscale/blob/v1.104.2/ipn/ipnstate/ipnstate.go).
Tailscale weist darauf hin, dass das JSON-Format versionsabhängig ist. Zusätzliche
Felder werden ignoriert; ungültige Pflichtfelder und ungültige Adressen werden abgewiesen.

`tests/rust/test-tailscale.py` prüft die tatsächlichen Rust-/GIO-Funktionen:

- Fehlende CLI: verständliche Meldung statt eines externen Fensters.
- Offizielle CLI ohne laufenden Dienst: Dienstfehler ohne rohe Standardfehlerausgabe.
- Separat gekennzeichnete CLI-Fixtures: ungültige JSON-Ausgabe, übergroße Ausgabe,
  hängender Prozess; Zeitlimit und anschließendes Einsammeln des Prozesses sind geprüft.
- Tatsächliche offizielle CLI und ein isolierter `tailscaled` im Userspace-Modus:
  `NeedsLogin` wird korrekt angezeigt, ohne Kontoanmeldung oder Tunnelaufbau.
- Mit `--ui`: tatsächliche GTK-VPN-Seite unter labwc/Wayland, Anzeige und erneute
  Abfrage des realen Dienststatus, genau ein App-Fenster.

Die Testumgebung verwendet ausschließlich die offiziellen, fest gepinnten
Tailscale-Archive 1.104.2 für amd64 und arm64. Die SHA-256-Werte stammen von den
[offiziellen Paketen](https://pkgs.tailscale.com/stable/) und werden vor dem
Entpacken geprüft. Diese Installation betrifft nur das kurzlebige Testimage;
auf dem Rampi-Gerät wird keine Software automatisch installiert oder aktualisiert.
Der Test startet nur seinen eigenen Dienst und verweigert den Start bei einem
bereits vorhandenen Socket. Er läuft ohne Netzwerk, Host-TUN-Gerät oder Host-VPN.

Nicht nachgewiesen: Anmeldung bei Tailscale, Gerätefreigabe, echtes Tailnet,
Verkehr zwischen Tailscale-Gegenstellen, Wiederverbindung nach externen Störungen
und vollständige grafische Einrichtung. Die positiven `Running`-/Online-Fälle
sind Parserprüfungen mit Schema-Fixtures, kein Beleg für echten Tunnelverkehr.
Physische Hardwaretests bleiben ausgeschlossen.
