# WLAN, Bluetooth und Login

Die aktuelle Rust-/GTK-Oberfläche verwendet eigene WLAN- und Bluetooth-Seiten
mit den vorhandenen NetworkManager-/BlueZ-Diensten über asynchrones GIO/D-Bus.
Es werden keine externen Netzwerk- oder Pairingfenster geöffnet. Die früheren
Python-/QML-Aufrufe von nm-connection-editor und Blueman gehören zum historischen
Prototyp, nicht zur nativen Sitzung.

NetworkManager verwaltet Netze, Kennwörter, gespeicherte Profile und Rechte.
Sichtbare und versteckte SSIDs, Adapterauswahl, offene Netze, WPA2 und WPA3/SAE
sind integriert. Neue Profile gehören dem tatsächlichen Linux-Konto und verbinden
sich ausschließlich manuell. Passende vorhandene Profile bleiben erhalten;
mehrdeutige Profile werden nicht automatisch ausgewählt. Unternehmensnetze
verwenden ein bereits administrativ eingerichtetes passendes NM-Profil.

BlueZ übernimmt Suche, Kopplung und Geräteverbindungen. Der eigene Agent zeigt
PIN, Passkey und Codevergleich als Rampi-Seiten. Geräte werden nach ausgewähltem
Adapter getrennt. Ein Adapter- oder Seitenwechsel gibt die eigene Suchverbindung
frei; verspätete Antworten können keine Suche zurücklassen. Vertrauen, Entfernen
und Abschalten eines Adapters erfordern Bestätigung, weil dies systemweit wirkt.

D-Bus-Aufrufe verlangen keine interaktive Polkit-Autorisierung über fremde
Programme. Vorhandene Systemrichtlinien entscheiden weiterhin über den Zugriff;
fehlende Berechtigungen werden innerhalb von Rampi angezeigt. Ein Administrator
muss notwendige Rechte bewusst über die vorhandenen Systemwerkzeuge einrichten.
Rampi installiert keine pauschalen Freigaben oder eigene Authentifizierung.
greetd/PAM verwenden die Linux-Konten; [zusätzliche Konten](NATIVE-USER-GUIDE.de.md)
werden bei Bedarf über vorhandenes sudo/useradd/passwd im VTE eingerichtet.

Der Installer stoppt bei aktivem dhcpcd oder ConnMan statt parallel einen
konkurrierenden Manager einzurichten. Eine Migration erfordert eine bewusste
Netzwerkkonfiguration, damit der Zugang zum Gerät nicht versehentlich abbricht.
