# Windows 11 Pro für RDP einrichten

Für Remote Desktop den Laptop eingeschaltet, geöffnet und erreichbar halten.
Jeder Rampi-Benutzer verwendet sein eigenes Windows-Konto mit minimalen Rechten.
Für RDP ist kein Rampi-Sitzungsadapter und keine Anbieter-CLI erforderlich.

1. In Windows Remote Desktop aktivieren. Alternativ zeigt das mitgelieferte
   `setup.ps1` zunächst nur den Bestand an; `-EnableRdp` aktiviert ausdrücklich
   den vorhandenen RDP-Dienst mit NLA und eine TCP-3389-Regel für private Netze.
   `-WhatIf` zeigt die vorgesehenen Änderungen. Keine dieser Aktionen geschieht
   beim bloßen Öffnen von Rampi.
2. Den Host über das gewählte VPN erreichbar machen. Firewallzugriff auf das
   eigene Netz begrenzen; Rampi öffnet keine Routerports.
3. Unter Einstellungen → Host & SSH das persönliche Hostprofil auswählen.
4. Remote Desktop → RDP öffnen. Port (normalerweise 3389), Windows-Konto und den
   unabhängig geprüften SHA256-Fingerabdruck des RDP-Serverzertifikats angeben.
   Das ist nicht der SSH-Hostfingerabdruck. Das Kennwort bleibt nur im laufenden
   Verbindungsaufbau und wird nicht in Einstellungen oder Befehlsargumenten gespeichert.
5. Strg+Alt+Pos1 führt zum Dashboard. Trennen meldet das Windows-Konto nicht ab.

OpenSSH ist für Administration optional. `-EnableOpenSsh` richtet ausdrücklich
den offiziellen Windows OpenSSH Server ein und erhält bestehende Konfigurationen.
Die eigene grafische Schlüsselverwaltung prüft Hostfingerabdrücke unabhängig und
verwendet den persönlichen OpenSSH-Agenten. Bestehende Schlüssel nicht ersetzen.

Die früheren Optionen `-Install` und `-InstallMissing` sowie das wirkungslose
Adapter-Update entfallen. Der persönliche KI-Adapter wird nicht mehr ausgeliefert.
Die Deinstallation kann eine alte Adapterdatei ausdrücklich entfernen;
Windows-Dienste, persönliche Daten und vorhandene Programme bleiben erhalten.

Die RDP-Softwareabnahme verwendet einen isolierten echten XRDP-Server auf Linux.
Ein Windows-Testhost wird auf Nutzerwunsch nicht verwendet; Windows-NLA ist damit
nicht als praktisch abgenommen ausgewiesen. [Streaming](STREAMING.md) bleibt separat.
