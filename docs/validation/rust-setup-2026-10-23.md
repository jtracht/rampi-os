# Rust-Einrichtung und persönliche Hosts

Lokale Softwareabnahme am 23. Oktober 2026 im isolierten Docker-Container,
labwc/Wayland, 1 GiB Speicherlimit und ohne Netzwerkzugang der grafischen Sitzung.
Keine physischen Hardwaretests.

`RAMPI_RUST_SETUP_HOSTS_OK` prüft die tatsächlichen GTK-Schaltflächen:

- Weiter, WLAN-Seite und Rückkehr ohne zusätzliches Fenster.
- Unterbrechen mit gespeichertem Schritt und ohne falschen Abschlussstatus.
- Zwei Hostprofile anlegen, zweites aktivieren und ungültigen SSH-Port ablehnen.
- Entfernen abbrechen sowie nach Bestätigung entfernen; aktives Profil bleibt gültig.
- Lokale Diagnose, Abschluss und erneutes Lesen der persönlichen Konfiguration.

Zwölf Core-Tests, Clippy mit abgewiesenen Warnungen und vollständiger nativer
Laufzeittest sind lokal erfolgreich. Die bestehende Abnahme für NetworkManager,
BlueZ, echte WireGuard-Gegenstellen, offiziellen Tailscale-Status, VTE, WebKit,
Kanban und tatsächlich wiedergegebenes Klicksignal bleibt erfolgreich.

Der Assistent enthält 15 Stationen, aber nicht 15 fertig implementierte
Einrichtungsfunktionen. Sprache/Tastaturlayout, Monitor- und Kontenverwaltung,
grafische Schlüsselbereitstellung, Anbieteranmeldung und Teile der
Tailscale-/Streaming-Einrichtung bleiben offen. Das steht unmittelbar in der
jeweiligen Seite. Abschließen ist eine bewusste Benutzerentscheidung und kein
Nachweis erfolgreicher Verbindungen. Bereits laufende Terminals behalten beim
Hostwechsel ihre bestehende Verbindung.
