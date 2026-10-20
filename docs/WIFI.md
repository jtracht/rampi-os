# WLAN

In **Einstellungen → System** WLANs suchen, ein Netz auswählen und mit Enter
verbinden. Neue WPA2-/WPA3-Personal-Netze zeigen ein maskiertes Kennwortfeld.
Das Feld wird nach dem Absenden, beim Netzwechsel und beim Verlassen der Ansicht
geleert. Offene Netze benötigen kein Kennwort. Die gesamte Bedienung ist per
Tab, Pfeiltasten und Enter erreichbar und läuft ohne blockierte Oberfläche.

Rampi liest Geräte, Signalstärke, Sicherheitsmerkmale und Verbindungszustand
über die offizielle NetworkManager-D-Bus-Schnittstelle. Eine Suche wartet im
Hintergrund auf `LastScan`; bei nicht verfügbarer oder noch laufender Suche
werden zuletzt bekannte Netze mit entsprechendem Hinweis angezeigt.
Versteckte SSIDs werden nicht geraten. Gleichnamige Netze werden pro Gerät,
roher SSID und Sicherheitsart zusammengefasst; SSIDs mit Doppelpunkt oder
Backslash werden nicht als getrennte Felder interpretiert.

Passende, vom Dienst als verfügbar gemeldete bestehende Profile werden ohne
Änderung aktiviert. Das umfasst bewusst bereits vorhandene gemeinsame Profile;
persönliche Profile anderer Linux-Benutzer werden ausgeschlossen. Rampi ruft
beim Anzeigen niemals `GetSecrets` auf. Für neue Netze validiert libnm sowohl
Einstellungen als auch Zugangsdaten. Neue Profile erhalten vor der Übergabe an
`AddAndActivateConnection2` die Berechtigung ausschließlich für die tatsächliche
Linux-UID und `autoconnect=false`. NetworkManager speichert das Kennwort mit
seinen eigenen Dateirechten und Berechtigungsprüfungen. Rampi speichert es weder
in persönlichen Einstellungen noch im Cache und übergibt es nicht in
Prozessargumenten. Kennwörter müssen während der Übergabe kurz im Prozessspeicher
vorliegen; ein garantiertes Überschreiben unveränderlicher Python-Zeichenketten
wird nicht behauptet.

„Verbunden“ wird erst nach dem aktivierten NetworkManager-Zustand angezeigt.
Fehler und ausbleibende Aktivierung ergeben eine Fehlermeldung; eine nach rund
60 Sekunden weiterhin ausstehende Aktivierung wird für den angeforderten
Verbindungsversuch beendet. Einzelne D-Bus-Aufrufe besitzen eigene Zeitlimits.
Trennen erhält das gespeicherte Profil. Neue Aufträge werden während laufender
WLAN-Operationen gesperrt. WLAN ein-/ausschalten gilt für das ganze Gerät;
NetworkManager und polkit entscheiden über die Freigabe.

**Erweiterte Netzwerkverwaltung** öffnet den vorhandenen `nm-connection-editor`.
Dort werden versteckte Netze, Unternehmens-WLAN, alte Sicherheitsverfahren,
Kennwortänderungen sowie besondere IP-/DNS-Einstellungen eingerichtet.
WEP-/WPA1-Netze werden in Rampi nicht auf offene Verbindungen herabgestuft.
Gespeicherte Profile mit Zugangsdaten eines separaten Secret-Agents benötigen
gegebenenfalls die erweiterte Verwaltung. Rampi ersetzt keinen solchen Agent.

## Nachweise und Grenzen

- Unit-Tests prüfen Zusammenfassung, Sicherheitszuordnung, fremde Profile,
  ausgeschalteten Funk, fehlende Netze, fehlgeschlagene Aktivierung und Timeout.
- `scripts/test-wifi-ui.py` verwendet die echte Qt-Oberfläche und GIO über einen
  isolierten D-Bus mit dem gepflegten **python-dbusmock**-NetworkManager-Template.
  Tastatureingabe, maskierte Darstellung, private Übergabe, kein Kennwort in
  Meldungen/Cache, Trennen, Suchen und Profilwiederverwendung werden geprüft.
  Die Aktivierung dieses Templates ist eine Test-Fixture, keine echte
  Funkverbindung und kein Nachweis einer WPA-Anmeldung oder DHCP über WLAN.
- `scripts/test-wifi-profile.py` läuft zusätzlich gegen einen **echten**
  NetworkManager in einem Wegwerf-Container: libnm validiert offene, WPA2- und
  SAE-Profile und lehnt ein ungültiges WPA2-Kennwort ab. Der Dienst speichert ein
  persönliches WPA2-Profil; Metadaten enthalten kein Kennwort und ein zweites
  Linux-Konto darf dessen Geheimnis nicht abrufen. Der Container hat kein
  Funkgerät und aktiviert dieses Profil nicht.

Physische Funkprüfungen sind auf ausdrücklichen Nutzerwunsch ausgeschlossen.
Die softwareseitige vollständige WPA-/DHCP-Verbindung bleibt offen.

Quellen: [NetworkManager Wireless API](https://networkmanager.dev/docs/api/latest/gdbus-org.freedesktop.NetworkManager.Device.Wireless.html),
[Aktivierung](https://networkmanager.dev/docs/api/latest/gdbus-org.freedesktop.NetworkManager.html),
[Sicherheitseinstellungen](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless-security.html),
[python-dbusmock](https://github.com/martinpitt/python-dbusmock).
