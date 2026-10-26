# Drei Hauptmodule und nachvollziehbare Umfangsänderung

Die Nutzerentscheidung vom 26.10.2026 entfernt Codex, Claude Code und
Gemini/Antigravity aus Rampi. Das Produkt besteht aus Kanban, Remote Desktop
und Browser; die lokale Systemkonsole und SSH-Verwaltung bleiben vorhanden.
Keine Anbieterinstallation, kein Modellaufruf und kein Windows-Testhost sind
Teil dieser Abnahme. Bereits vorhandene Programme und persönliche Daten bleiben
erhalten. Alte veröffentlichte Images werden nicht verändert.

Entfernt sind die drei Dashboardkacheln, Vorschauen, GTK-Seiten, CLI-Start- und
Sitzungsaktionen, drei Assistentenschritte, der Windows-KI-Adapter und dessen
zusätzliche psmux-Installation. Auch der historische Python-Prototyp bietet diese
Startwege nicht mehr an. Seine Regression prüft tatsächliche alte Modulaufrufe:
kein Prozessstart, verständlicher Fehler und unverändertes persönliches Profil.
Alte Projektfelder bleiben zur verlustfreien Konfigurationskompatibilität lesbar,
werden aber nicht mehr als Einrichtungsfeld angeboten oder ausgeführt.

Die ergänzende Bereinigung entfernt außerdem unaufgerufene allgemeine
PowerShell-/SSH-Starthelfer, den in Rust nicht verwendeten externen FreeRDP-
Starter, versteckte Projekt-Eingabewidgets, fünf unreferenzierte Symbolgrafiken
und das nicht mehr benötigte Windows-Adapter-Updateskript samt Installationsflags.
Die aktuelle Oberfläche verwendet ausschließlich die drei passenden Modulicons.
Das persönliche Modell erhält alte Projektwerte beim Bearbeiten eines Hosts;
dies prüft die echte GTK-Hostbearbeitung. Die eingebettete RDW-/IronRDP-Verbindung,
OpenSSH-Schlüsselverwaltung und lokale Systemterminals bleiben erhalten.

Die erste neue Imageprüfung deckte eine übrig gebliebene Diagnoseabhängigkeit
auf: `gdbus` wurde nur zum Protokollieren von Schlüsselbundmetadaten verwendet,
musste aber im netzunabhängigen QEMU-Gast nachinstalliert werden. Diese Ausgabe
und Abhängigkeit entfallen. Tatsächliches Speichern/Laden über den Rust-Adapter,
Dateitrennung und erneute PAM-Anmeldung bleiben unverändert. Benötigte Testtools
werden vor dem Boot bereitgestellt; während der Abnahme werden keine Pakete oder
Bibliotheken des installierten Gasts aktualisiert.

Der GTK-Test aktiviert alle drei tatsächlichen Dashboardkacheln, prüft ihre
Zielseiten und den Rückweg sowie genau ein Fenster. Der Container hat dabei
keinen Netzwerkzugang. Er verlangt zusätzlich drei Kacheln und keine alten
KI-Seiten. Die Eingabe-/Animationsabnahme vermisst nun die violette Remote-Kachel
mit denselben Mindestbewegungen an allen vier Kanten. Reduzierte Bewegung muss
weiterhin still bleiben. RDP, Browser, Kanban/Gitea, persönliche Profile und
die bisherigen Sicherheitsprüfungen bleiben verpflichtend.

Die zehnminütige Mischlast verwendet weiterhin drei wirkliche VTE-Prozesse;
dies sind generische lokale Testkonsolen, keine integrierten KI-Anwendungen.
Die obsolete Anbieterprüfung entfällt mit der entfernten Funktion. Keine
verbleibende RDP-, PAM-, Netzwerk-, Quellen- oder Imageprüfung wird abgeschwächt.

## Bewertung

Die frühere Bewertung war 81/100 bei zwanzig Bereichen. Der entfallene Bereich
Anbieter-CLIs hatte drei von fünf Punkten: die vergleichbare Basis ist damit
78/95 = 82,1 %, nicht etwa 81/95. Gelöschte Funktionen erhalten keine Punkte.

Die Zielabnahme ergänzt drei belegbare Punkte im verbleibenden Umfang:

- Dashboard 4→5: alle nun vereinbarten Hauptmodule sind eingebettet, ihre
  tatsächlichen Hin-/Rückwege und Offline-Bedienung werden auf beiden
  Architekturen geprüft; echte Modulabnahmen bleiben zusätzlich Pflicht.
- Installer/Reparatur 4→5: nativer HTTPS-Bootstrap, atomare Aktivierung und
  Rückwechsel sind bereits geprüft; hinzu kommen die Erhaltungswächter für
  vorhandene Dienste, Schlüsselbünde, Symlinks und private Homes sowie frische
  PAM-Anmeldungen beider Konten mit dem wirklichen Installerprofil.
- GitHub/CI/CD 4→5: der vollständige native Entwicklungsrelease wurde mit
  frischem Image veröffentlicht und unabhängig heruntergeladen. Alle 28 Assets,
  Git-Tag, Server-Digests, vollständige APT-/Cargo-Quellen und grafischen Belege
  sind geprüft. Quellen über 2 GiB werden verlustfrei in geprüften Teilen verteilt.

Damit ergibt sich nach vollständiger neuer nativer CI und unabhängiger Prüfung
ihrer heruntergeladenen Belege **81/95 = 85,3 %** des reduzierten Umfangs.
Bis zu dieser Abnahme ist dies ein Zielwert. Ein fehlgeschlagener oder noch
laufender Test gibt den zusätzlichen Dashboard-/Installerpunkt nicht frei.
Die Punkte für Dokumentation und Systemimage bleiben bei vier; ein reguläres
vollständiges Produkt, Windows-NLA und eingebettetes Streaming werden nicht
als fertig ausgegeben. Frühere 81 % und neue 85,3 % haben verschiedene Nenner.

## Zugehörige Nachweise

- [Veröffentlichtes natives Entwicklungsrelease](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.1),
  Quelle `cb5cebcc9fb958cca2652d799e531cb8243e0fb3`, Release-Lauf
  [40234594283](https://github.com/jtracht/rampi-os/actions/runs/40234594283).
- [PAM-Integration](pam-keyring-ordering-2026-10-25.md): erneute Anmeldungen,
  tatsächlicher Rust-Secret-Service-Adapter und fremde Dateizugriffe auf beiden
  Architekturen; [PR 46](https://github.com/jtracht/rampi-os/pull/46).
- [Nativer Installer](rust-native-2026-10-23.md),
  [HTTPS-Bootstrap und Handbetrieb](../NATIVE-OPERATIONS.de.md).
- Die neue CI muss die Marker `RAMPI_RUST_NO_PROVIDER_ROUTES_OK` und
  `RAMPI_RUST_THREE_MODULE_NAVIGATION_OK` sowie alle weiterhin erforderlichen
  nativen, RDP-, PAM-, Radio- und Paketbelege erzeugen. Die unabhängige Prüfung
  bindet ARM64-Programmhash, getesteten Merge-Baum und sieben Paketprüfsummen.
