# Fehlerdiagnose

**Dashboard bleibt ohne Host nutzbar:** Hostausfall ist kein Fehler der lokalen
Sitzung. Host/VPN und persönliche SSH-Identität getrennt prüfen.

**SSH bricht sofort ab:** known_hosts, Port, Konto, Schlüssel und Windows-Adapter
prüfen. Hostprüfung nicht deaktivieren. Windows-Benutzer-PATH muss codex/claude/agy
und psmux enthalten. Rampi startet keine erfundene `antigravity`-CLI.

**Vorhandene Sitzung zeigt altes Projekt:** psmux verbindet bewusst erneut.
Anbietersitzung gezielt beenden und mit neuem Projekt öffnen.

**Linux-Dienst nicht verfügbar:** `installer/raspberrypi/diagnostics.sh` nutzen.
Auf Windows sind NetworkManager/BlueZ erwartbar nicht vorhanden. Keine grünen
Verbindungsanzeigen daraus ableiten.

**Polkit verweigert eine Änderung:** Mit persönlichem Konto und vorhandenen
Systemrechten arbeiten. Nicht die gesamte Oberfläche als root starten.

**Kanban zeigt Offline-Cache:** Datenquelle/Berechtigung prüfen und aktualisieren.
Cache wird ausdrücklich als solcher markiert; ein leeres neues Profil zeigt
keine erfundenen Aufgaben.

**Streaming schlägt fehl:** Pairing, Sunshine-Desktop-Anwendung und Decoder prüfen.
Keine Legacy-Firmwareoptionen ungeprüft übernehmen. Ein laufendes RDP-Modul ist
kein Beleg dafür, dass Streaming auf derselben Hardware funktioniert.
