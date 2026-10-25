# Tatsächlicher Gitea-Server und native Kanban-Seite

Die zusätzliche Abnahme verwendet das offizielle Gitea 28.2.0, festgelegt auf
Image-Digest `sha256:30777c91280d973fa02be48b1ade735bd6859e8f6f7af3b4444d519437852504`.
Sie erzeugt ausschließlich neue Docker-Volumes, ein internes Netzwerk ohne
veröffentlichte Ports und ein privates Testrepository. Vorhandene Gitea-Instanzen
und persönliche Konten werden nicht angesprochen.

Giteas eigener `cert`-Befehl erstellt das kurzlebige TLS-Zertifikat. Nur dessen
öffentlicher Teil wird im Wegwerfclient als CA installiert. Rampi verwendet
unverändert curl mit Zertifikatsprüfung; es gibt weder `--insecure` noch
nachgebildete API-Antworten. Gitea startet direkt unter seiner normalen UID,
ohne zusätzlichen SSH-Dienst.

Der Server erstellt ein Repository-Projekt mit zwei Aufgaben und einer leeren
Spalte. Das API-Seitenlimit beträgt absichtlich eins. Rampi muss trotzdem beide
Aufgaben und die leere Spalte laden. Der Client erhält ausschließlich einen
Token mit `read:repository,read:issue`; ein echter Schreibversuch wird mit HTTP
403 abgewiesen. Ein separater Setup-Token bleibt im Testcontroller und erreicht
den Rampi-Prozess nicht.

Die tatsächliche GTK-Einstellungsseite speichert den Zugang im vorhandenen
verschlüsselten GNOME-Schlüsselbund und leert das Kennwortfeld. Die Kanban-Seite
zeigt das reale Board im einzigen Rampi-Fenster. Der Controller verändert eine
Aufgabe serverseitig; nach erneutem Laden muss die Suche diese neue Aufgabe
anzeigen. Anschließend prüft der Controller alle tatsächlichen Aufgaben über
mehrere API-Seiten und schaltet Gitea aus. Die Oberfläche behält beide Aufgaben
mit ausdrücklichem Offline-Hinweis. Ein fremdes Zugangsprofil erhält keinen Cache.

`tests/rust/test-cloud-kanban.py` stellt dieselbe bestehende Schlüsselbundhülle
auch für diesen Test bereit. Die ursprünglichen sechs Anbieter-Vertragsprüfungen
bleiben getrennt erhalten und bestehen nach dieser Wiederverwendung erneut.
Es werden keine Modellanfragen ausgelöst.

Lokal bestehen der reale Serverlauf, die unabhängige Artefaktprüfung und die
synthetischen Negativtests des Prüfers. Auch die kombinierte AMD64-/ARM64-CI
und die unabhängige Prüfung ihrer heruntergeladenen Nachweise bestehen. Diese
Abnahme belegt Repository-Projekte
dieser Gitea-Version; weitere Projekttypen und persönliche Anbieterzugänge bleiben
offen. Der Prozentstand steigt durch diese zusätzliche Prüfung allein nicht.

Wiederholung nach dem nativen Rust-Build:

```sh
python3 tests/rust/test-gitea-live.py --image rampi-rust-dev
python3 scripts/check-gitea-evidence.py artifacts/gitea-live
```

Die Ausgaben enthalten Programm-SHA256, Serverversion, Image-Digest,
serverseitig geprüfte Aufgaben, Phasenquittungen und ein tatsächliches
Compositor-PNG. Sie enthalten keine Tokens, privaten Schlüssel oder persönlichen
Kontodaten. Sämtliche neu erzeugten Docker-Ressourcen werden danach entfernt.

## Zusammenführung

Die [native CI 40134255831](https://github.com/jtracht/rampi-os/actions/runs/40134255831)
und [allgemeine CI 40134255825](https://github.com/jtracht/rampi-os/actions/runs/40134255825)
sind vollständig erfolgreich. Neben den beiden echten Gitea-Läufen bestehen die
heruntergeladenen Laufzeit-, Funk- und Login-Nachweise sowie sieben Paketprüfsummen
erneut die eingefrorenen unabhängigen Prüfer; ARM64 einschließlich Installer.
Der Geheimnisscan ist unverändert aktiv. Er hatte den öffentlichen Image-Digest
als möglichen Schlüssel markiert; ausschließlich dieser konkrete öffentliche
Wert ist jetzt präzise gekennzeichnet. Der vollständige Scan besteht ebenfalls.

* Akzeptierter PR-Stand: `9d12bbd661e7822f4614f94f66b1ec128460891a`.
* Gebauter kombinierter Stand: `64e028c0bf39db31674889660897a389a4f06bad`.
* [PR #40](https://github.com/jtracht/rampi-os/pull/40), zusammengeführt als
  `68ba794549fdb68459e319db9b25a3973d0023a8`.
* Identischer getesteter und zusammengeführter Tree:
  `cd4c577de7a34133a63094eb0b192f0fb443a374`.
* ARM64-Paketprogramm, auch gegen beide tatsächlichen grafischen Sitzungen geprüft:
  `2bc24aaa4d746d9d40b472ca6cd64ee090e43773cd52d46581d01925caaa2ed0`.
