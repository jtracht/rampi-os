# RDP-Maus und Zwischenablage · 24.10.2026

Der tatsächliche XRDP-Testserver empfängt jetzt die Maus- und Tastaturereignisse
in einer gewöhnlichen Tk/X11-Anwendung seines normalen Testkontos. Das ist keine
RDP-Simulation: Rampi verbindet seinen bestehenden RDW-/IronRDP-Client über TLS
mit XRDP/Xorg. Nur der Testhost verwendet X11; der Client bleibt GTK/Wayland.
Die vorhandene Xterm-Anwendung des zehnminütigen Mischbetriebs bleibt bestehen.

## Änderung

Der erste neue Test deckte auf, dass RDW jede innerhalb des eigenen GTK-Prozesses
erzeugte Zwischenablage als Echo behandelte. Damit kamen insbesondere Kopien
aus Rampi-Feldern nicht beim Host an. Die lokale Anpassung vergleicht jetzt den
tatsächlichen vom Remote-Desktop angebotenen ContentProvider. Sie unterdrückt
nur dessen Echo; eigene neue Kopien können in beide Richtungen übertragen werden.
Der Provider wird lediglich schwach referenziert.

Die Unicode-Behandlung nutzt außerdem die bereits vorhandenen IronRDP-Helfer
`new_unicode_string` und `to_unicode_string`, einschließlich des vollständigen
UTF-16-Abschlusses. Der separate lokale Textcodec entfällt. Die Protokoll- und
TLS-Implementierungen bleiben bei den vorhandenen Bibliotheken.

## Tatsächliche lokale Abnahme

- Dasselbe Rampi-Fenster empfängt echte Remote-Frames, weist ein falsches
  Zertifikat zurück und verbindet nach Trennung erneut.
- Tatsächliche Wayland-Pointer-Eingaben erreichen den Testhost: linke, mittlere
  und rechte Taste jeweils gedrückt/freigegeben. Die Koordinaten entsprechen
  der skalierten GTK-Fläche mit einer Toleranz für Pixelrundung.
- Beide Scrollachsen funktionieren in beiden Richtungen. Die Rohereignisse
  enthalten den X11-Modifikatorzustand. Der verwendete Tk-Empfänger meldet
  horizontales Scrollen als Shift+Mausrad; andere Empfänger können Tasten 6/7
  melden. Der Prüfer verlangt horizontale und vertikale Nachweise ausdrücklich
  getrennt. Doppelte vertikale Ereignisse reichen nicht.
- Zwei aufeinanderfolgende Textkopien durchlaufen jeweils Rampi → Host → Rampi.
  Eine frische Testkennung, Umlaute, ein Zeichen außerhalb der BMP und ein
  Zeilenumbruch müssen erhalten bleiben. Ausschließlich CRLF/LF werden bei
  diesem Textvergleich gleichgesetzt.
- Strg+Alt+Pos1 führt zum Dashboard. Der Host erhält keine Pos1-Taste;
  nach Rückkehr funktionieren normale Remote-Eingaben ohne hängenbleibende
  Modifikatortasten. Die Sitzung bleibt bis zum ausdrücklichen Trennen aktiv.

`rdp-input.json`, `remote-events.jsonl` und `keyboard-receipts.txt` enthalten die
Messdaten und tatsächlichen Serverquittungen. `check-rdp-input-evidence.py` prüft
sie erneut nach dem Download. Sechzehn synthetische Prüfer-Tests prüfen nur die
Zurückweisung unvollständiger Nachweise; sie ersetzen keine Laufzeitabnahme.

Die lokale Abnahme mit 1 GiB/vier CPUs, Clippy und Ruff besteht. Die vollständige
native CI ist inzwischen auf AMD64 und ARM64 akzeptiert. Das ist keine
Windows-NLA- oder Windows-11-Pro-Abnahme; ein entsprechender Testhost ist
nicht vorhanden. Eingebettetes Streaming und weitere Remote-Abnahmen bleiben
offen. Der Gesamtstand wird dadurch noch nicht erhöht.

## Zusammenführung und unabhängige Artefaktprüfung

Die [native CI 40116926807](https://github.com/jtracht/rampi-os/actions/runs/40116926807)
und [allgemeine CI 40116926756](https://github.com/jtracht/rampi-os/actions/runs/40116926756)
sind vollständig erfolgreich. Beide heruntergeladenen Laufzeitnachweise bestehen
erneut den eingefrorenen unabhängigen Prüfer einschließlich der tatsächlichen
Maus-, Scroll- und Unicode-Serverquittungen. Beide frischen grafischen Anmeldungen
und Funkläufe sowie alle sieben Paketprüfsummen bestehen ebenfalls; ARM64 mit
Installer. Der erste CI-Lauf bestand bereits die Eingabeabläufe, scheiterte aber
anschließend an den Leserechten des erzeugten `rdp-input.json`. Der Testcontainer
veröffentlicht jetzt ausschließlich seine nicht geheimen Nachweisdateien lesbar
für den aufrufenden Prüfer. Der abschließende Lauf bestätigt diesen Weg.

* PR-Quellstand: `e34e5b11f94d1dbada3ef0f30c8dcb386af08ec0`.
* Gebauter kombinierter Stand: `41a22465bb1e1f2563a5d1e1b1e7fec12a53526c`.
* [PR #39](https://github.com/jtracht/rampi-os/pull/39), zusammengeführt als
  `6083a7a6ea5720a8b0528a87b59b65946f129759`.
* Identischer getesteter und zusammengeführter Tree:
  `73c93772ba2a15c9cd300bf300be46974aa8bc11`.
* ARM64-Paketprogramm, zusätzlich gegen beide echten grafischen Login-Sitzungen
  geprüft: `57494c7411c6cd9c77f0cf0edf469a90e23c5f06dfa5bf03107ce788b87fe3bd`.

Grundlagen: [RDW-Quellzuordnung und lokale Anpassungen](../../vendor/rdw/README.rampi.md),
[Tk-Bindings und horizontales Scrollen](https://web.tcl.tk/man/tcl9.1/TkCmd/bind.html),
[XRDP-Eingabeverarbeitung](https://github.com/neutrinolabs/xrdp/blob/v0.10.1/xrdp/xrdp_wm.c).
