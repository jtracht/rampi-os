# Drei Hauptmodule und nachvollziehbare UmfangsÃ¤nderung

Die Nutzerentscheidung vom 26.10.2026 entfernt Codex, Claude Code und
Gemini/Antigravity aus Rampi. Das Produkt besteht aus Kanban, Remote Desktop
und Browser; die lokale Systemkonsole und SSH-Verwaltung bleiben vorhanden.
Keine Anbieterinstallation, kein Modellaufruf und kein Windows-Testhost sind
Teil dieser Abnahme. Bereits vorhandene Programme und persÃ¶nliche Daten bleiben
erhalten. Alte verÃ¶ffentlichte Images werden nicht verÃ¤ndert.

Entfernt sind die drei Dashboardkacheln, Vorschauen, GTK-Seiten, CLI-Start- und
Sitzungsaktionen, drei Assistentenschritte, der Windows-KI-Adapter und dessen
zusÃ¤tzliche psmux-Installation. Auch der historische Python-Prototyp bietet diese
Startwege nicht mehr an. Seine Regression prÃ¼ft tatsÃ¤chliche alte Modulaufrufe:
kein Prozessstart, verstÃ¤ndlicher Fehler und unverÃ¤ndertes persÃ¶nliches Profil.
Alte Projektfelder bleiben zur verlustfreien KonfigurationskompatibilitÃ¤t lesbar,
werden aber nicht mehr als Einrichtungsfeld angeboten oder ausgefÃ¼hrt.

Der GTK-Test aktiviert alle drei tatsÃ¤chlichen Dashboardkacheln, prÃ¼ft ihre
Zielseiten und den RÃ¼ckweg sowie genau ein Fenster. Der Container hat dabei
keinen Netzwerkzugang. Er verlangt zusÃ¤tzlich drei Kacheln und keine alten
KI-Seiten. Die Eingabe-/Animationsabnahme vermisst nun die violette Remote-Kachel
mit denselben Mindestbewegungen an allen vier Kanten. Reduzierte Bewegung muss
weiterhin still bleiben. RDP, Browser, Kanban/Gitea, persÃ¶nliche Profile und
die bisherigen SicherheitsprÃ¼fungen bleiben verpflichtend.

Die zehnminÃ¼tige Mischlast verwendet weiterhin drei wirkliche VTE-Prozesse;
dies sind generische lokale Testkonsolen, keine integrierten KI-Anwendungen.
Die obsolete AnbieterprÃ¼fung entfÃ¤llt mit der entfernten Funktion. Keine
verbleibende RDP-, PAM-, Netzwerk-, Quellen- oder ImageprÃ¼fung wird abgeschwÃ¤cht.

## Bewertung

Die frÃ¼here Bewertung war 81/100 bei zwanzig Bereichen. Der entfallene Bereich
Anbieter-CLIs hatte drei von fÃ¼nf Punkten: die vergleichbare Basis ist damit
78/95 = 82,1 %, nicht etwa 81/95. GelÃ¶schte Funktionen erhalten keine Punkte.

Die Zielabnahme ergÃ¤nzt drei belegbare Punkte im verbleibenden Umfang:

- Dashboard 4â†’5: alle nun vereinbarten Hauptmodule sind eingebettet, ihre
  tatsÃ¤chlichen Hin-/RÃ¼ckwege und Offline-Bedienung werden auf beiden
  Architekturen geprÃ¼ft; echte Modulabnahmen bleiben zusÃ¤tzlich Pflicht.
- Installer/Reparatur 4â†’5: nativer HTTPS-Bootstrap, atomare Aktivierung und
  RÃ¼ckwechsel sind bereits geprÃ¼ft; hinzu kommen die ErhaltungswÃ¤chter fÃ¼r
  vorhandene Dienste, SchlÃ¼sselbÃ¼nde, Symlinks und private Homes sowie frische
  PAM-Anmeldungen beider Konten mit dem wirklichen Installerprofil.
- GitHub/CI/CD 4â†’5: der vollstÃ¤ndige native Entwicklungsrelease wurde mit
  frischem Image verÃ¶ffentlicht und unabhÃ¤ngig heruntergeladen. Alle 28 Assets,
  Git-Tag, Server-Digests, vollstÃ¤ndige APT-/Cargo-Quellen und grafischen Belege
  sind geprÃ¼ft. Quellen Ã¼ber 2 GiB werden verlustfrei in geprÃ¼ften Teilen verteilt.

Damit ergibt sich nach vollstÃ¤ndiger neuer nativer CI und unabhÃ¤ngiger PrÃ¼fung
ihrer heruntergeladenen Belege **81/95 = 85,3 %** des reduzierten Umfangs.
Bis zu dieser Abnahme ist dies ein Zielwert. Ein fehlgeschlagener oder noch
laufender Test gibt den zusÃ¤tzlichen Dashboard-/Installerpunkt nicht frei.
Die Punkte fÃ¼r Dokumentation und Systemimage bleiben bei vier; ein regulÃ¤res
vollstÃ¤ndiges Produkt, Windows-NLA und eingebettetes Streaming werden nicht
als fertig ausgegeben. FrÃ¼here 81 % und neue 85,3 % haben verschiedene Nenner.

## ZugehÃ¶rige Nachweise

- [VerÃ¶ffentlichtes natives Entwicklungsrelease](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.1),
  Quelle `cb5cebcc9fb958cca2652d799e531cb8243e0fb3`, Release-Lauf
  [40234594283](https://github.com/jtracht/rampi-os/actions/runs/40234594283).
- [PAM-Integration](pam-keyring-ordering-2026-10-25.md): erneute Anmeldungen,
  tatsÃ¤chlicher Rust-Secret-Service-Adapter und fremde Dateizugriffe auf beiden
  Architekturen; [PR 46](https://github.com/jtracht/rampi-os/pull/46).
- [Nativer Installer](rust-native-2026-10-23.md),
  [HTTPS-Bootstrap und Handbetrieb](../NATIVE-OPERATIONS.de.md).
- Die neue CI muss die Marker `RAMPI_RUST_NO_PROVIDER_ROUTES_OK` und
  `RAMPI_RUST_THREE_MODULE_NAVIGATION_OK` sowie alle weiterhin erforderlichen
  nativen, RDP-, PAM-, Radio- und Paketbelege erzeugen. Die unabhÃ¤ngige PrÃ¼fung
  bindet ARM64-Programmhash, getesteten Merge-Baum und sieben PaketprÃ¼fsummen.
