# VPN

Tailscale und WireGuard sind gleichberechtigte Optionen in den Einstellungen.
Tailscale wird über die offizielle CLI aufgerufen; der vorhandene Daemon bleibt
für Authentifizierung und Routing verantwortlich. `tailscale up` kann eine URL
oder fehlende Berechtigungen ausgeben. Rampi räumt sich keine Operatorrechte ein.
Eine Tailscale-Installation fehlt auf dem aktuellen Entwicklungsrechner.

WireGuard-Konfigurationen werden als `.conf` bis 64 KiB über NetworkManager
importiert. Zum Verbinden/Trennen dient die eindeutige Verbindungs-UUID.
Vor Aktivierung in nm-connection-editor automatische Aktivierung deaktivieren
und die Zugriffsberechtigung auf das persönliche Linux-Konto begrenzen. Der
aktuelle Importpfad muss noch um diese automatische Einschränkung ergänzt werden.
Ein importiertes Profil wird von Rampi nicht explizit aktiviert.

Beide VPNs verändern systemweite Routen. Persönliche Konfigurationen sind keine
eigenen Netzwerk-Namespaces. Linux-Rechte/polkit müssen Mehrbenutzerbedienung
korrekt begrenzen. Gleichzeitige Default-Routen und Exit-Nodes zunächst
diagnostizieren; keine stillen Route-Änderungen oder automatische VPN-Auswahl.
Es gibt weder eine eigene Kryptografie noch eine neue VPN-Protokollimplementierung.

https://tailscale.com/kb/1031/install-linux
https://www.wireguard.com/install/
