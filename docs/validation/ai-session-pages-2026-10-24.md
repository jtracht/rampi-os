# Native KI-Einrichtung und Sitzungsseiten

Die drei KI-Kacheln und die entsprechenden Stationen des Einrichtungsassistenten
öffnen eigene Rust-/GTK-Seiten im bestehenden Fenster. Eine asynchrone,
zeitlich und mengenmäßig begrenzte SSH-Prüfung fragt den persönlichen
Windows-Adapter ab: CLI vorhanden, psmux vorhanden, exakte Sitzung vorhanden.
Fehlende Programme sind keine erfolgreiche Einrichtung. Anbieteranmeldungen
werden ausdrücklich als ungeprüft angezeigt und nicht aus Dateien ausgelesen.

Die offizielle Anleitung wird im eingebetteten WebKit-Browser geöffnet, auch
wenn dieser bereits existiert. Eine Sitzung kann wiederverbunden oder nach
einer gesonderten Bestätigung gezielt beendet werden. Abbrechen führt keine
Sitzungsaktion aus. Terminalflächen sind an Host, SSH-Port und Windows-Konto
gebunden; ein anderes Profil öffnet nicht versehentlich ein fremdes Terminal.
Während der Einrichtung führt Zurück zum aktuellen Schritt.

## Prüfungen und Grenzen

* Lokales Windows: der tatsächliche Adapter erkennt installierte Codex- und
  Claude-Programme und fehlendes `agy`/psmux. Keine Modellanfrage wurde ausgelöst.
* Rust-Core: feste erlaubte Aktionen, kodierte PowerShell-Literale einschließlich
  Apostrophen im Projektpfad, verbindliche Hostschlüsselprüfung und kein
  interaktiver Hintergrund-Prompt (`BatchMode=yes`, ohne PTY).
* Tatsächliches GTK unter Wayland: drei Modulseiten, fehlender Host, positive und
  fehlende CLI, laufende/gestoppte Sitzung, Bestätigung und Abbruch, ungültiges
  JSON, abgewiesener SSH-Aufruf und weiterhin genau ein Anwendungsfenster.
  Dieser Teil verwendet ausdrücklich einen SSH-Vertragsadapter, keinen
  Windows- oder Anbieter-Ersatznachweis.
* Windows-CI erweitert den bisherigen echten psmux-Test um die neue Check-Aktion
  vor und nach dem Stoppen einer wirklichen Sitzung; die benachbarte Sitzung
  muss erhalten bleiben. Die tatsächliche Windows-SSH-Prüfung beendet außerdem
  den Transport des offiziellen Rampi-Adapters abrupt und verbindet dieselbe
  native Sitzung mit unveränderter Prozessidentität erneut. Der Providerprozess
  ist ausdrücklich ein Heartbeat-Testprogramm, keine Modellanfrage.

Akzeptiert: [native CI 40092593930](https://github.com/jtracht/rampi-os/actions/runs/40092593930)
auf AMD64 und ARM64 sowie [allgemeine CI 40092593918](https://github.com/jtracht/rampi-os/actions/runs/40092593918)
einschließlich Windows. Heruntergeladene native Nachweise, beide frischen grafischen
Anmeldungen und sieben Paketprüfsummen wurden unabhängig erneut geprüft.
[PR 33](https://github.com/jtracht/rampi-os/pull/33) wurde mit identischem geprüften
Git-Baum `295d0392c778ea6ed6cb3b20e1c893cbbace894f` zusammengeführt.

Persönliche Anbieteranmeldungen, tatsächliche Modellantworten und die
zusammenhängende Windows-11-Pro-Abnahme bleiben separat offen. Der Gesamtstand
bleibt bis zur vollständigen Bereichsabnahme bei 80/100.
