# Bluetooth

Unter **Einstellungen → System → Bluetooth** den Adapter wählen und einschalten.
**Geräte suchen** startet eine eigene BlueZ-Suchanfrage; ein vorhandener Suchlauf
anderer Anwendungen wird nicht beendet. Beim Verlassen der Systemseite gibt
Rampi seine eigene Suchanfrage frei. Geräte werden mit Namen, Adresse und
tatsächlichem Kopplungs-/Verbindungszustand angezeigt. Auswahl und Aktionen sind
mit Tab, Pfeiltasten und Enter bedienbar.

**Koppeln** verwendet `org.bluez.Device1.Pair`. Rampi registriert dafür einen
anwendungsspezifischen BlueZ-Agenten mit `KeyboardDisplay` und verdrängt keinen
vorhandenen Standardagenten. Die Oberfläche zeigt Vergleichscodes, einzugebende
PINs/Passkeys und Codes für externe Tastaturen. Vergleich oder Freigabe müssen
bewusst bestätigt werden; Escape lehnt die Anfrage ab. Neue Codes haben eine
eigene Anfragekennung. Normale Statusaktualisierungen löschen keine laufende
Eingabe. Unbeantwortete Anfragen werden nach 60 Sekunden abgelehnt. BlueZ kann
eine Kopplung unabhängig davon früher abbrechen.

Nur der bei D-Bus registrierte eindeutige Besitzer von `org.bluez` darf Methoden
des Agenten aufrufen. Andere Prozesse werden auch bei gleicher Linux-UID
abgewiesen. PINs und Codes befinden sich ausschließlich im Arbeitsspeicher;
Rampi protokolliert oder speichert sie nicht. Ein Dienstneustart verwirft offene
Anfragen und veraltete Gerätedaten. **Aktualisieren** registriert den Agenten am
neuen Dienst erneut. Die eigene GLib-Ereignisschleife bedient die offizielle
asynchrone GIO-Schnittstelle; das Qt-Fenster bleibt während der Kopplung bedienbar.

Nach dem Koppeln kann **Verbinden** die unterstützten BlueZ-Profile aktivieren.
Ein erfolgreiches Koppeln allein behauptet keine bestehende Profilverbindung.
Geräte ohne einen verbindbaren Dienst können die Verbindung ablehnen.
**Trennen** erhält die Kopplung. **Dauerhaft vertrauen** und **Kopplung entfernen**
verlangen eine ausdrückliche Bestätigung mit festgehaltener Geräteadresse.
Neue Geräte erhalten nicht automatisch dauerhaftes Vertrauen.

Adapterzustand, Kopplungsschlüssel und Vertrauen gelten **systemweit**. BlueZ
und die vorhandene Betriebssystemrichtlinie prüfen die Berechtigungen. Rampi
führt keine zusätzliche Benutzer- oder Schlüsseldatei und startet keinen zweiten
Bluetooth-Dienst. Das Ausschalten kann die gerade verwendete Tastatur/Maus
trennen und verlangt deshalb eine Bestätigung. Die erweiterte Verwaltung öffnet
bei Bedarf das vorhandene Blueman.

## Softwareprüfungen

`scripts/test-bluetooth-ui.py` verwendet die tatsächliche Qt-Oberfläche und GIO
auf einem isolierten D-Bus mit dem gepflegten BlueZ-Template von python-dbusmock.
Geprüft werden fremde Aufrufer, bewusster Codevergleich, PIN-/Passkey-Eingabe,
Tastaturcodeanzeige, Ablehnen/Abbrechen, Suche, Koppeln, Verbinden, Trennen,
bestätigtes Vertrauen/Entfernen und ein Dienstneustart. Alte Template-Versionen
aktualisieren bei Connect/Disconnect nur Signale; die Test-Fixture synchronisiert
zusätzlich ihre über `GetManagedObjects` gemeldeten Eigenschaften. Dies ist
ausdrücklich eine Schnittstellenprüfung und kein HCI-/Funkkopplungsnachweis.

Die zusätzliche QEMU-Umgebung hat zwei echte virtuelle HCI-Controller über
BlueZ `btvirt` und den Linux-Treiber `hci_vhci` nachgewiesen. Die vollständige
Kopplung darüber ist noch in Arbeit. Physische Funkgeräte bleiben auf
Nutzerwunsch aus dem Testumfang ausgeschlossen.

Quellen: [BlueZ Agent API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Agent.rst),
[Device API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Device.rst),
[Adapter API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Adapter.rst).
