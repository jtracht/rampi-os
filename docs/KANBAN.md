# Schreibgeschütztes Kanban

Im Kanban-Modul zeigt die Kopfzeile sichtbare und gesamte Kartenzahl.
Projekt, Priorität und Status besitzen getrennte, tastaturbedienbare Auswahllisten.
Sie werden mit der Suche kombiniert: Eine Karte muss alle gewählten Bedingungen
erfüllen. Suche berücksichtigt Titel, Beschreibung, Projekt, Priorität und Status.
**Zurücksetzen** entfernt alle Filter und die Suchanfrage.

Auswahllisten basieren auf der vollständigen Quelle, auch wenn einzelne Karten
gerade ausgefiltert sind. Normales Aktualisieren erhält die Auswahl. Entfernt die
Quelle einen ausgewählten Wert, wird dieser Filter zurückgesetzt. Beim Wechsel
der Datenquelle oder des Credential-Profils werden alte Inhalte und Filter
verworfen; verspätete Antworten der vorherigen Quelle werden ignoriert.

Unter **Einstellungen → Kanban & Browser** lässt sich eine persönliche
Spaltenreihenfolge mit einem Namen pro Zeile speichern. Leer übernimmt die
Reihenfolge der Datenquelle. Unbekannte Statuswerte erscheinen automatisch rechts.
Leere, doppelte, überlange Namen und Steuerzeichen werden vor dem Speichern
abgewiesen. Dies ändert ausschließlich die lokale Anzeige; Statuswerte und Karten
auf GitHub, Trello, Jira, Asana, Notion oder in der JSON-Datei bleiben erhalten.

Karten lassen sich öffnen und lesen; es existieren keine Aktionen zum Erstellen,
Bearbeiten, Verschieben oder Löschen. Datenquelle und eingeschränkte Zugangsdaten:
[Konfiguration](CONFIGURATION.md). Persönliche Anbieter-Anmeldungen sind weiterhin
keine durch Vertragstests ersetzte Live-Abnahme. [Testumfang](TESTING.md).
