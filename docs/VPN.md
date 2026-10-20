# VPN

Tailscale und WireGuard sind gleichberechtigte Optionen in den Einstellungen.
Tailscale wird über die offizielle CLI aufgerufen; der vorhandene Daemon bleibt
für Authentifizierung und Routing verantwortlich. `tailscale up` kann eine URL
oder fehlende Berechtigungen ausgeben. Verbindungsänderungen rufen die root-eigene
offizielle CLI über pkexec auf; die vorhandene polkit-Oberfläche authentifiziert
den Administrator. Rampi räumt sich keine stillen Operatorrechte ein.
Das Image enthält Tailscale; bestehende Installationen werden wiederverwendet.

WireGuard-Konfigurationen werden als `.conf` bis 64 KiB über NetworkManager
importiert. Zum Verbinden/Trennen dient die eindeutige Verbindungs-UUID.
Der offizielle libnm-Parser liest die Datei; Rampi setzt vor dem AddConnection2-
D-Bus-Aufruf die persönliche Benutzerberechtigung und deaktiviert Autostart.
Damit existiert kein vorübergehend gemeinsam nutzbares Profil. Der echte
Trixie-libnm-Test bestätigt beide Eigenschaften. Import aktiviert keine Verbindung.

Beide VPNs verändern systemweite Routen. Persönliche Konfigurationen sind keine
eigenen Netzwerk-Namespaces. Linux-Rechte/polkit müssen Mehrbenutzerbedienung
korrekt begrenzen. Gleichzeitige Default-Routen und Exit-Nodes zunächst
diagnostizieren; keine stillen Route-Änderungen oder automatische VPN-Auswahl.
Es gibt weder eine eigene Kryptografie noch eine neue VPN-Protokollimplementierung.

https://tailscale.com/kb/1031/install-linux
https://www.wireguard.com/install/
