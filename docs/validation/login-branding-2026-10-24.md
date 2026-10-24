# Rampi-Anmeldung mit Originalgrafik · 24.10.2026

Geprüfte Wiederverwendung: wlgreet 0.5 besitzt konfigurierbare RGBA-Farben und
eine Overlay-Fläche mit exklusiver Tastatur, aber keine Logoansicht. ReGreet
würde einen weiteren, separat zu bauenden Greeter einführen. Rampi behält deshalb
das vorhandene wlgreet/greetd/PAM und ergänzt ausschließlich einen GTK-Hintergrund.

Der besondere Programmstart `--login-background` erzeugt eine eigenständige
Logoansicht ohne Arbeitsmodule, Kontoverwaltung, Zugangsdaten oder Authentifizierung.
Er verwendet das gelieferte Original-PNG unverändert als installierte Datei;
GTK skaliert es für die Anzeige. Eine helle Fläche erhält die Lesbarkeit des
dunklen Original-Schriftzugs. wlgreet liegt darüber, verarbeitet die Tastatur und
führt die vollständige Anmeldung durch. Der Startwrapper beendet den Hintergrund,
wenn wlgreet endet; ein Fehlschlag lässt keine Arbeitsumgebung ohne Anmeldung zu.

Lokal sind die tatsächlichen GTK- und wlgreet-Flächen gemeinsam unter Wayland
mit 1 GiB dargestellt und visuell geprüft. Zehn Installer-Prüfungen bestehen:
Migration nur der exakten aufgezeichneten Rampi-Standardkonfiguration,
wiederholte Migration sowie Erhalt eigener Login-Befehle, Farben, Profile,
veränderter Prüfsummen und symbolischer Links.

Die frische grafische QEMU-Abnahme verlangt ein sichtbares farbiges Logo,
exakt einen Hintergrundprozess mit ausschließlich diesem Startargument und
keine Arbeitsoberfläche vor der Anmeldung, auch nach der globalen Tastenkombination.
Falsches PAM-Kennwort, zwei normale Linux-Konten, echte sichtbare Arbeitsflächen,
private SSH-Agenten und Rückkehr zur Anmeldung bleiben Pflicht. Diese erweiterten
Nachweise auf AMD64 und ARM64 sind bis zum erfolgreichen CI-Lauf offen. Die
physische Hardwareabnahme bleibt wie vereinbart ausgeschlossen.
