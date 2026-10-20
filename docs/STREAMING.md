# Streaming und Windows-Konten

RDP und Sunshine erfüllen unterschiedliche Aufgaben. FreeRDP meldet dich mit
deinem Windows-Konto an. Sunshine/Moonlight teilen die aktive Windows-Konsole;
eine Gerätekopplung ist keine Windows-Benutzeranmeldung. Für gemeinsam genutzte
Hosts und getrennte Windows-Konten RDP verwenden. Rampi richtet keine parallelen
Windows-Desktops und keinen zusätzlichen Sitzungsbroker ein.

Sunshines vorhandener Windows-Dienst beobachtet die aktive Konsolensitzung und
startet seinen Capture-Prozess beim Sitzungswechsel neu. Eine alleinige Abfrage
des angemeldeten Kontos vor dem Verbindungsaufbau wäre deshalb keine verlässliche
Zugriffssperre. Rampi gibt eine solche Abfrage nicht als Benutzerisolation aus.
Quellennachweis: [offizieller Sunshine-Dienst](https://github.com/LizardByte/Sunshine/blob/8aac196bb879f10698b40b1c4c7a6d212d9d022b/tools/sunshinesvc.cpp).

## Persönliche Kopplung

1. In den Host-Einstellungen den gewünschten Host und das eigene Windows-Konto wählen.
2. Im Remote-Desktop-Modul **Streaming-Host koppeln** öffnen und den Moonlight-PIN
   in der vorhandenen Sunshine-Verwaltung bestätigen.
3. Danach **Windows-Konsole teilen · Moonlight** öffnen.

Rampi übergibt Moonlight Embedded bei Kopplung und Streaming dasselbe explizite
`-keydir`. Die Schlüssel liegen unter
`$XDG_CONFIG_HOME/rampi/streaming/<SHA256>/`, sonst unter
`~/.config/rampi/streaming/<SHA256>/`. Verzeichnisse haben unter Linux Modus 0700.
Der Hash berücksichtigt Hostadresse, SSH-Port und Windows-Kontonamen; Namen des
Profils und Projektwechsel ändern die Kopplung nicht. Andere Linux-Benutzer haben
eigene Verzeichnisse. Der laufende Streamingprozess verwendet den beim Start
ausgewählten Schlüsselpfad.

Bestehende Moonlight-Standardschlüssel werden erhalten und nicht automatisch in
mehrere persönliche Profile kopiert. Nach einem Update auf getrennte Profile
ist deshalb einmalig die Kopplung für jedes verwendete Host-/Windows-Profil nötig.
Ohne persönliche Kopplungsdateien zeigt Rampi einen Einrichtungshinweis.
Sunshine verwaltet weiterhin selbst seine gekoppelten Geräte und deren Widerruf.
Getrennte lokale Schlüssel erzwingen keine Windows-Kontenzuordnung auf Sunshine.

Das vorhandene X11-/SDL-/FFmpeg-Streaming bleibt bei 720p, 30 FPS und 5 Mbit/s
als Standard. Physische GPU- und Latenztests sind auf Nutzerwunsch ausgenommen.
Die [Softwaretests](TESTING.md) unterscheiden Protokoll-/Systemtests von
persönlichen Verbindungen und Hardwaremessungen.
