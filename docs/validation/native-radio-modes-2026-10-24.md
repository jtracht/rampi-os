# Native WLAN-Sicherheitsmodi und virtuelle BlueZ-Kopplung

Die tatsächliche Rust-/GIO-Implementierung wird im QEMU-Gast als gewöhnlicher
Linux-Benutzer gegen NetworkManager, wpa_supplicant, hostapd und BlueZ geprüft.
Es werden keine Host-Funkgeräte oder physischen Raspberry-Pi-Geräte verwendet.

## Lokale Entwicklung

Der ausdrücklich als vorbereitet gekennzeichnete lokale Debian-Gast besteht:

* WPA2 sowie reines WPA3/SAE und eine versteckte WPA3-SSID: Anmeldung, privates
  gespeichertes Profil, DHCP-Adresse, tatsächlicher IP-Rundlauf, falsches Kennwort,
  Trennen und Wiederverbindung. Ein zweites Linux-Konto kann in keinem Modus das
  persönliche Profil übernehmen. Der WPA3-Nachweis verlangt ausdrücklich SAE;
  ein Rückfall auf WPA2 zählt nicht. Das versteckte Profil muss `hidden=true` besitzen.
* Zwei offizielle btvirt-/Kernel-VHCI-Controller: tatsächliche Entdeckung und
  Kopplung über den produktiven Rust-Adapter, Paired auf beiden Seiten und
  tatsächliche LinkKey-Abschnitte in beiden BlueZ-Bindungsdateien. Schlüssel werden
  weder ausgegeben noch exportiert. Anschließend Vertrauen zurücknehmen, entfernen,
  abgewiesener Zugriff auf den entfernten Gerätepfad und Adapter aus-/einschalten.

Der Testpartner verwendet den vorhandenen bluetoothctl-Agenten mit
NoInputNoOutput. Das ersetzt weder die gesonderten Rampi-Agent1-PIN-/Passkey-Tests
noch einen HID-/Funk-/Treibernachweis. Der erste Entwicklungslauf scheiterte an
der nicht abgewarteten Agentbereitschaft; der korrigierte Lauf wartet auf echte
Registrierung und Freigabe des offiziellen Agenten.

## Oberfläche und Berechtigungen

Die GTK-Seite zeigt nur Geräte des ausgewählten Adapters. Der tatsächliche
Zwei-Adapter-Test prüft Listenwechsel und Freigabe der eigenen Suchverbindung
bei Adapter- und Seitenwechsel. Erneutes Suchen ersetzt den bisherigen Suchclient,
damit nach einem Dienst-/Controllerneustart keine verlorene Suche blockiert.
Die GTK-Prüfung verwendet weiterhin eine klar getrennte D-Bus-Fixture.

Produktive D-Bus-Aufrufe fordern keine interaktive Polkit-Autorisierung über
fremde Anwendungen an. Vorhandene Systemrichtlinien bleiben verbindlich;
fehlende Rechte erscheinen innerhalb von Rampi. BlueZ-Agentfragen verwenden
weiterhin die integrierten PIN-/Passkey-Seiten.

## Freigabebedingung

Der vorbereitete lokale Gast ist Entwicklungsnachweis, keine frische Abnahme.
Vor Zusammenführung verlangt die CI auf AMD64 und ARM64 jeweils einen neuen
Gast aus dem festgelegten offiziellen Debian-Image. Der unabhängige Prüfer
verlangt alle Laufzeitmarker, alle drei Kontentrennungen, das exakte native
Prüfprogramm mit ELF-Architektur und SHA256 sowie die zugesagten 1 GiB/vier CPUs.
Vorbereitete oder fortgesetzte Gäste und fehlende Ergebnisse werden abgewiesen.
Der herunterladbare Prüfcode erhält die ursprünglichen Rust-Lizenzen.

Der erste vollständige CI-Lauf zeigte zwei Fehler der Testumgebung:
Auf AMD64 bestanden sämtliche Funkprüfungen, danach fehlten dem Runner die
Schreibrechte für die Lizenzkopien im vom Container angelegten Verzeichnis.
Die Dateien werden jetzt im selben Container kopiert. Der offizielle ARM64-
Generic-Kernel enthält kein VHCI-Modul. Nur der bezeichnete Wegwerf-Gast baut
deshalb den unveränderten vorhandenen Linux-Treiber `hci_vhci.c` aus dem
versionsgleichen offiziellen Debian-Kernelquellpaket gegen die Header des
laufenden Kernels. Quellversion, Kernel und SHA256 werden protokolliert. Weder
Produktinstallation noch Kernel-Bootdateien werden dadurch verändert; alle
Bluetooth-Laufzeitprüfungen bleiben verpflichtend. Ein fehlendes passendes
Quell-/Headerpaket oder ein Ladefehler lässt die Abnahme fehlschlagen.

Der anschließende ARM64-Lauf bestätigt den erfolgreichen Aufbau und das Laden
dieses Treibers. Das tatsächliche ARM64-ELF benötigt außerdem `libgtk-4.so.1`;
der Gast installiert dafür jetzt das vorhandene Debian-Laufzeitpaket. Der
Prüfprozess verwendet weiterhin keinen Display-Server. Ein separater sporadischer
Login-Prüffehler entstand beim Lesen der noch leeren UID-Nachweisdatei zwischen
Dateierstellung und `id`-Ausgabe. Die Testhülle veröffentlicht den vollständig
geschriebenen Wert jetzt durch Umbenennen. Die tatsächliche UID muss weiterhin
exakt mit dem authentifizierten Linux-Konto übereinstimmen.

## Frische kombinierte CI akzeptiert

Die [native CI 40110643882](https://github.com/jtracht/rampi-os/actions/runs/40110643882)
und [allgemeine CI 40110643836](https://github.com/jtracht/rampi-os/actions/runs/40110643836)
sind auf beiden Architekturen erfolgreich. Die heruntergeladenen Laufzeit-,
Funk- und Anmeldenachweise sowie alle sieben Paketprüfsummen bestehen nochmals
unabhängig die eingefrorenen Prüfer. Der getestete Tree ist unverändert nach
main zusammengeführt; Quellstände und Programmhash stehen im
[81-Prozent-Nachweis](rust-native-81-2026-10-24.md). WLAN erhält damit seinen
fünften Punkt, die übrigen Bereichswerte bleiben unverändert.
