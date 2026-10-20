# Persönliche Konfiguration

Datei: `$XDG_CONFIG_HOME/rampi/settings.json`, sonst `~/.config/rampi/settings.json`.
Atomare Ersetzung; Linux-Verzeichnis 0700 und Datei 0600. Fehlerhafte Dateien
werden nicht überschrieben. Unbekannte Felder stoppen das Laden.

| Einstellung | Typ / Standard | Zweck und Wirkung |
|---|---|---|
| language | string / de | Vorgesehene UI-Sprache; der erste Stand ist deutsch |
| setup_complete | bool / false | Einrichtungshinweis; keine Änderung an Linux-Konten |
| active_host | int / 0 | Index des aktiven Hosts |
| hosts | array / [] | Persönliche Windows-Profile; grafisch unter Host & SSH verwalten und aktivieren |
| hosts[].name | string / Windows | Anzeigename des Hosts |
| hosts[].address | string / leer | geprüfter DNS-Name/IP ohne Shellzeichen |
| hosts[].username | string / leer | eigenes Windows-Konto |
| hosts[].port | int / 22 | SSH-Port 1–65535 |
| hosts[].identity | string / leer | existierender privater SSH-Schlüsselpfad; kein Schlüsselinhalt |
| hosts[].project | string / leer | zugängliches Projektverzeichnis auf Windows |
| hosts[].resolution | string / 1280x720 | bevorzugte Moonlight-Streamingauflösung |
| browser_url | string / https://www.raspberrypi.com | HTTPS-Startseite ohne eingebettete Credentials |
| board_source | string / leer | JSON-Dateipfad oder anbieterspezifische Projektkennung |
| board_kind | enum / json | json, github, trello, jira, asana, notion |
| board_token_key | string / leer | persönlicher Secret-Service-Profilname; niemals der Token selbst |
| board_columns | string[] / [] | persönliche Spaltenreihenfolge; leer übernimmt Quelle; höchstens 32 eindeutige, nicht leere Namen mit je 1–80 Zeichen |
| reduce_motion | bool / false | schaltet die Kachelverformung aus |

Zugangsdaten können unter Einstellungen → Kanban im persönlichen Secret Service
gespeichert werden. Der Profilname wird in der Konfiguration gespeichert, der
Token ausschließlich über die Standardeingabe an `secret-tool` übergeben.
Alternativ den bestehenden Secret Service direkt verwenden, zum Beispiel:
`secret-tool store --label='Rampi GitHub read-only' application rampi profile github-work`.
Die Eingabe erfolgt interaktiv. Token nicht in Shellargumente, Git oder JSON kopieren.

Quellenformate: GitHub `organization/NAME/PROJEKTNUMMER` oder
`user/NAME/PROJEKTNUMMER`; Trello Board-ID; Asana numerische Projekt-ID;
Notion Data-Source-ID. Jira Cloud: `https://SITE.atlassian.net#PROJEKT`,
mit Secret-Service-Wert `{"email":"…","token":"…"}`. OAuth verwendet stattdessen
`https://api.atlassian.com/ex/jira/CLOUD-UUID#PROJEKT` und einen Bearer-Token.
Trello speichert seinen Secret-Service-Wert als `{"key":"…","token":"…"}`.
Die Beispiele enthalten keine echten Credentials.

Unter Einstellungen → Host & SSH Hostschlüssel abrufen und die angezeigten
SHA256-Fingerprints unabhängig am Windows-Host vergleichen (siehe Windows-Anleitung).
Erst danach die Bestätigung aktivieren und speichern. Vorhandene abweichende
Hostschlüssel werden nicht überschrieben; Änderungen müssen unabhängig geprüft werden.

Kanban-Cache: `$XDG_CACHE_HOME/rampi/board-<SHA256>.json`, sonst `~/.cache/rampi/`.
Der Hash trennt Anbieter, Quelle und Credential-Profil. Inhalte können vertraulich
sein und gehören nur dem jeweiligen Linux-Benutzer. Cache kann manuell gelöscht
werden. Browserprofil: `~/.config/rampi/browser/`.

Die Kanban-Spalten stehen unter Einstellungen → Kanban & Browser, ein Name je
Zeile. Zusätzliche Statuswerte aus den Karten werden rechts angefügt und niemals
versteckt oder umgeschrieben. [Bedienung und Filter](KANBAN.md).
Die drei Auswahlfilter und die Suchanfrage gelten für die laufende Oberfläche,
werden gemeinsam angewendet und verändern keine Anbieter-Daten. Quellenwechsel
setzt sie zurück; normale Aktualisierung erhält noch vorhandene Filterwerte.

Moonlight-Kopplungsschlüssel: `~/.config/rampi/streaming/<SHA256>/`, getrennt nach
Hostadresse, SSH-Port und Windows-Konto. Kopplung und Streaming verwenden denselben
persönlichen Schlüsselpfad; bestehende globale Moonlight-Schlüssel werden nicht
übernommen. [Einrichtung und Kontengrenzen](STREAMING.md).
