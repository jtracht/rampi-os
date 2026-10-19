# WLAN, Bluetooth und Login

NetworkManager verwaltet Netzwerkprofile. Der Client liest Status und WLANs
asynchron über die NetworkManager-D-Bus-Schnittstelle und nmcli.
Passwörter, Zertifikate und Profilrechte werden im bestehenden
nm-connection-editor eingestellt; Rampi legt keine eigene Passwortdatei an.
BlueZ und Blueman übernehmen Pairing, Agentenfragen und Geräteverbindungen.
Fehlende Programme erzeugen eine nachvollziehbare Fehlermeldung.

Die direkte vollständige grafische D-Bus-Verwaltung ist im ersten Stand noch
nicht implementiert. Die eingebundenen vorhandenen Dialoge sind echte Systemtools.
LightDM/PAM verwenden bestehende Linux-Konten. Rampi erzeugt keine unabhängige
Benutzerdatenbank, umgeht keine polkit-Entscheidung und startet nicht als root.

Der Installer stoppt bei aktivem dhcpcd oder ConnMan statt parallel einen
konkurrierenden Manager einzurichten. Eine Migration erfordert eine bewusste
Netzwerkkonfiguration, damit der Zugang zum Gerät nicht versehentlich abbricht.
