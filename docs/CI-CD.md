# CI/CD

CI läuft bei Push auf main und bei Pull Requests. Linux und Windows prüfen
Python-Lint, Typen, Unit-Tests, echten QML-Start und Pakete. Bash erhält ShellCheck;
Windows erhält statische PowerShell-Analyse der verbleibenden Installer.
Die entfernten KI-Sitzungsadapter und ihre psmux-Prüfungen gehören nicht mehr zum Produkt.
Runtime-Abhängigkeiten werden mit pip-audit geprüft; detect-secrets und die
Lizenz-/Herkunftsdokumentprüfung ergänzen die Prüfung.

Actions sind auf Commit-SHAs festgelegt. Pull Requests bekommen nur Leserechte;
Release-Schreibrechte gelten nur für den Releasejob. Kein pull_request_target
führt fremden Quellcode mit Secrets aus. Prüfen von Lizenzdokumenten ersetzt
keine vollständige juristische Drittanbieteranalyse.

Image-Build ist separat manuell auslösbar und wird vom nativen Entwicklungsrelease
verwendet. v0.6.0-dev.1 wurde mit frischem Image und vollständig geprüften öffentlichen
Downloads veröffentlicht. Fehlgeschlagene Images werden nicht veröffentlicht. Releasebereitschaft
wird aus `packaging/readiness.json` gelesen. Die Nutzerentscheidung ersetzt die
Hardwarepflicht durch Softwareabnahme: Trixie-ARM64-Docker, AccountsService/PAM,
integriertes RDP gegen isoliertes XRDP und Image-/QEMU-Validierung. Fehlende physische Tests
blockieren den vereinbarten Softwareumfang nicht.
