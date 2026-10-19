# CI/CD

CI läuft bei Main-/Feature-/Fix-Push und Pull Requests. Linux und Windows prüfen
Python-Lint, Typen, Unit-Tests, echten QML-Start und Pakete. Bash erhält ShellCheck;
Windows erhält PowerShell-Analyse und einen isolierten nativen psmux-Test.
Runtime-Abhängigkeiten werden mit pip-audit geprüft; detect-secrets und die
Lizenz-/Herkunftsdokumentprüfung ergänzen die Prüfung.

Actions sind auf Commit-SHAs festgelegt. Pull Requests bekommen nur Leserechte;
Release-Schreibrechte gelten nur für den Releasejob. Kein pull_request_target
führt fremden Quellcode mit Secrets aus. Prüfen von Lizenzdokumenten ersetzt
keine vollständige juristische Drittanbieteranalyse.

Image-Build ist separat manuell auslösbar und wird später vom Releaseworkflow
verwendet. Fehlgeschlagene Images werden nicht veröffentlicht. Releasebereitschaft
wird aus `packaging/readiness.json` gelesen. Die Nutzerentscheidung ersetzt die
Hardwarepflicht durch Softwareabnahme: Trixie-ARM64-Docker, AccountsService/PAM,
native Windows-SSH-Prüfungen und Image-/QEMU-Validierung. Fehlende physische Tests
blockieren den vereinbarten Softwareumfang nicht.
