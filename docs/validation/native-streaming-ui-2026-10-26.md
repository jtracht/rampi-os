# Eingebettetes Streaming: Kriterien vor der Abnahme

Der bestätigte Stand bleibt **81/95 = 85,3 %**. Diese Erweiterung ist bis zur
vollständigen Prüfung und Zusammenführung Entwicklungsarbeit. Ein lokaler Lauf
eines nicht eingecheckten Programms ist ausdrücklich keine endgültige Abnahme.

Die Rampi-Seite verwendet vorhandene Moonlight-C-/Rust-Schnittstellen,
libcurl/OpenSSL, GStreamer und GTK. Es gibt keinen eigenen Streaming-Protokollstack,
Player oder Display-Server. Neue Kopplungen und gespeicherte Identitäten liegen
im vorhandenen persönlichen Secret Service. Projekt-/Anbieterterminals werden
nicht wieder eingeführt.

Die verpflichtende Prüfung verwendet einen echten isolierten Sunshine-Server:
PIN-Kopplung, gespeicherten Server-Schlüssel, Ablehnung eines geänderten Schlüssels,
zwei Verbindungen mit wechselnden H.264-Bildern, tatsächliches empfangenes 997-Hz-
Stereo-Audio, GTK-Texturen und Bildschirmaufnahmen. Beide GTK-Verbindungen müssen
über den wirklichen persönlichen Schlüsselbund laufen und im selben Fenster bleiben.
Alte Bilder müssen beim Trennen und Verlassen verschwinden. Das reservierte
Dashboard-Kürzel muss über die tatsächliche Compositor-Bindung funktionieren.

Sunshine protokolliert zusätzlich seine tatsächlich entschlüsselten Eingabepakete:
R/Return jeweils drücken und loslassen auf beiden Verbindungen, skalierte absolute
Mauspositionen, linker Klick und beide Scrollachsen. Home darf beim reservierten
Kürzel nicht beim Server ankommen. Die Plattform-Eingabeausführung im Testserver
bleibt abgeschaltet; diese Paketquittungen sind keine Windows- oder HID-Abnahme.
Nur die erforderlichen Paketfelder werden exportiert, keine vollständigen
Debug-Anfragen oder privaten Kopplungsdaten.

## Dauerlast unter festem Ressourcenbudget

Zusätzlich zu den vorhandenen Modulwechsel-, Mischlast- und Ressourcenprüfungen
muss das wirkliche GTK-Streaming **600 Sekunden** eine bewegte 720p/30-Testquelle
empfangen. FFplay erzeugt das Bild ausschließlich auf dem isolierten Testserver;
der Client verwendet ausschließlich die eingebettete GTK-Seite. Client und Server
laufen jeweils mit 1 GiB RAM, ohne zusätzlichen Swap und mit vier CPUs.

Vor dem Lauf gelten folgende Grenzen:

- Mindestens 12.000 neue GTK-Texturen und 1.000 unterschiedliche Bildproben.
- Tatsächliche Paint-Messungen für mindestens 90 % der neuen Texturen.
- 95. Perzentil von Texturveröffentlichung bis GTK-After-Paint höchstens 80 ms.
- Höchster gemessener Programm-RSS höchstens 512 MiB; RSS-Zuwachs höchstens 64 MiB.

Die Messungen kommen aus dem tatsächlichen GTK-Frameclock und Linux-Prozessstatus.
Die Ressourcenbegrenzung wird aus Docker ausgelesen, die Bilddaten stammen aus
dem wirklichen decodierten Stream. Fehlende, verkürzte, nicht endliche oder
falsch zugeordnete Messungen werden abgewiesen. Ein bestehender kurzer Videotest
ersetzt diesen Dauerlauf nicht. Eine Messung auf einem echten Pi ist ausgeschlossen.

## Konten, Installation und Image

Frische grafische PAM-Anmeldungen auf AMD64 und ARM64 müssen zusätzlich den
Streaming-Schlüsselbundpfad speichern und nach erneuter Anmeldung lesen. Eine
andere Hostbindung darf den persönlichen Eintrag nicht finden. Vorhandene
Kontentrennung, Datei- und Busrechte sowie die übrigen Prüfungen bleiben Pflicht.

Der Installer muss eine vorhandene kompatible Bibliothek unverändert verwenden,
auch über einen bestehenden Symlink. Eine inkompatible Datei darf er nicht
überschreiben. Falls die Laufzeit fehlt, wird ausschließlich das vorhandene
offizielle C-Bibliotheksziel gebaut. Vollständige Quellen, Lizenzen, gesperrte
Git-Revisionen und Programmprüfsumme begleiten das neue Image.

Vor endgültiger Freigabe sind die nativen Nachweise beider Architekturen,
Paket-/Programm-/Quellzuordnung sowie eine frische grafische Image-Abnahme nötig.
Ein vorhandenes veröffentlichtes Image wird niemals ersetzt. Für eine neue
Veröffentlichung müssen tatsächlich heruntergeladene Release-Dateien zusätzlich
geprüft werden. Windows-Testhosts, Modellanfragen und physische Hardware bleiben
ausgeschlossen; diese Grenzen ändern sich durch einen erfolgreichen Test nicht.
