# Architektur

Raspberry Pi OS Lite Trixie arm64 ist laut offizieller Kompatibilitätsliste für
Pi 3 B+ geeignet. Der 64-Bit-Stack vereinfacht die Verwendung gepflegter Qt-Pakete.
Die Entscheidung ist keine RAM-Messung. Die 1-GB-Zielgröße muss real geprüft werden.

LightDM übernimmt PAM, Linux-Konten, Xorg und die virtuelle Konsole. Openbox führt
Fensterwechsel und globale Tastenkombinationen aus. Rampi startet weder einen
eigenen Displayserver noch eine zweite Desktopumgebung. X11 wurde für den ersten
Stand wegen der vorhandenen FreeRDP-/VTE-/Chromium-Integration gewählt. Wayland
mit labwc bleibt eine mögliche Alternative nach Messung der Decoder- und
Shortcut-Kompatibilität. SDL wäre für ein reines Dashboard geeignet, würde aber
mehr eigene Formular-/Fokusintegration erfordern. GTK/VTE ist eine Alternative;
Qt Quick vereint portable Entwicklung und vorhandene Pfadanimationen.

Das unprivilegierte Python-Backend verwendet einen auf drei Threads begrenzten
Qt-Workerpool. Zeitbegrenzte Systemaufrufe und HTTP-Zugriffe blockieren keine
Animationen. Es gibt keinen lokalen HTTP-Server und keinen neuen Netzwerkport.
Qt Quick rendert die Oberfläche; native externe Anwendungen übernehmen die
ressourcenintensiven Module. xfce4-terminal verwendet die etablierte VTE-Engine.
Der aktuelle Stand steuert externe Fenster; er bettet sie nicht in Qt ein.

OpenSSH authentifiziert das persönliche Windows-Konto. Ein winziger
PowerShell-Adapter startet die offiziellen CLIs in einem vorhandenen nativen
psmux-Server mit ConPTY. Ein Rampi-eigener Sitzungsserver ist nicht notwendig.
Die Windows-Berechtigungen gelten weiterhin. Reattach verwendet denselben
Sitzungsnamen pro Anbieter und Benutzer; Projektwechsel für eine vorhandene
Sitzung erfordern bewusstes Beenden dieser Sitzung.

Quellen, geprüft 19.10.2026:
- https://www.raspberrypi.com/software/operating-systems/
- https://packages.debian.org/trixie/python3-pyside6.qtquick
- https://github.com/psmux/psmux
- https://github.com/RPi-Distro/pi-gen/tree/arm64
