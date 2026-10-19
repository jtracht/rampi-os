import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
  id: wizard
  title: "Rampi einrichten"
  modal: true
  property int step: 0
  signal settingsRequested(int page)
  readonly property var steps: [
    {title: "Sprache & Tastatur", text: "Die Oberfläche dieses Entwicklungsstands ist deutsch. Passe Tastatur und Maus im vorhandenen Systemdialog an. Die Systemsprache wird bei der Raspberry-Pi-Ersteinrichtung festgelegt.", action: "keyboard", label: "Tastatur und Maus"},
    {title: "HDMI-Anzeige", text: "Wähle eine gut lesbare Auflösung für Bildschirm oder Beamer. Rampi verändert keine Firmware- oder Bootoptionen.", action: "display", label: "Anzeige einstellen"},
    {title: "WLAN", text: "NetworkManager verwaltet WLANs und Zugangsdaten. Die Einrichtung erfolgt im vorhandenen grafischen Systemdialog.", action: "wifi-connect", label: "WLAN einrichten"},
    {title: "Bluetooth", text: "Kopple Tastatur und Maus über BlueZ und den vorhandenen Pairingdialog. Halte für die erste Einrichtung eine USB-Tastatur bereit.", action: "bluetooth", label: "Geräte koppeln"},
    {title: "Linux-Konto & Login", text: "Du bist bereits mit deinem persönlichen Linux-Systemkonto angemeldet. LightDM und PAM verwalten den Login. Neue Konten müssen mit den regulären Linux-Systemwerkzeugen angelegt werden; die eigene grafische Kontenverwaltung ist noch nicht implementiert.", action: "", label: ""},
    {title: "VPN", text: "Wähle Tailscale oder WireGuard. Beachte die systemweiten Routingauswirkungen und die Berechtigungen anderer Benutzer.", page: 2, label: "VPN-Einstellungen"},
    {title: "Windows-Host", text: "Verwende einen eingeschalteten Windows-11-Pro-Laptop und dein eigenes Windows-Konto. Der Host-Installer prüft vorhandene Dienste vor Änderungen.", page: 0, label: "Host konfigurieren"},
    {title: "SSH-Schlüssel", text: "Erzeuge einen persönlichen Schlüssel. Übertrage nur den öffentlichen Teil auf Windows und prüfe den Host-Fingerprint unabhängig, bevor du ihn akzeptierst.", action: "ssh-key", label: "Schlüssel erzeugen"},
    {title: "ChatGPT / Codex", text: "Die offizielle native Windows-Codex-CLI muss im persönlichen Windows-Konto installiert und angemeldet sein. psmux hält den Prozess bei Modulwechseln am Leben.", module: "codex", label: "Codex öffnen"},
    {title: "Claude Code", text: "Installiere Claude Code über den offiziellen Windows-Installationsweg und melde dich im persönlichen Konto an. Die offiziellen Sicherheitsdialoge bleiben erhalten.", module: "claude", label: "Claude Code öffnen"},
    {title: "Antigravity", text: "Die offizielle Antigravity-CLI heißt agy. Eine andere oder erfundene CLI wird nicht als Ersatz gestartet.", module: "antigravity", label: "Antigravity öffnen"},
    {title: "Desktop-Streaming", text: "Sunshine und Moonlight Embedded benötigen vorheriges Pairing. Die Pi-3-B+-Decodierung und der zuverlässige Betrieb unter Trixie müssen noch auf Hardware abgenommen werden.", module: "stream", label: "Streaming prüfen"},
    {title: "Remote Desktop", text: "FreeRDP verbindet mit Microsoft RDP. Kennwörter werden interaktiv abgefragt. Prüfe das Zertifikat vor dem ersten Vertrauen; Windows erlaubt nur eine interaktive Desktopsitzung.", module: "rdp", label: "RDP prüfen"},
    {title: "Kanban & Browser", text: "Richte eine lokale JSON-Datei oder einen lesenden Cloud-Connector ein. Cloud-Zugänge sind noch nicht gegen persönliche Konten validiert. Dein Browser verwendet ein eigenes Profil.", page: 3, label: "Datenquellen einrichten"},
    {title: "Abschlussdiagnose", text: "Prüfe die tatsächlich installierten Programme. Eine erfolgreiche Diagnose bestätigt keine noch nicht durchgeführten Hardware- oder Verbindungstests. Du kannst alle Einstellungen später ändern.", action: "diagnostics", label: "Diagnose anzeigen"}
  ]
  contentItem: ColumnLayout {
    spacing: 24
    Label { text: (wizard.step + 1) + " / " + wizard.steps.length; opacity: 0.65 }
    ProgressBar { from: 0; to: wizard.steps.length; value: wizard.step + 1; Layout.fillWidth: true }
    Label { text: wizard.steps[wizard.step].title; font.pixelSize: 30; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Label { text: wizard.steps[wizard.step].text; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 17; lineHeight: 1.5 }
    Button {
      visible: wizard.steps[wizard.step].label !== ""
      text: wizard.steps[wizard.step].label
      onClicked: {
        let current = wizard.steps[wizard.step];
        if (current.page !== undefined) wizard.settingsRequested(current.page);
        else if (current.module !== undefined) rampi.launch(current.module);
        else if (current.action) rampi.action(current.action, "");
      }
    }
    Item { Layout.fillHeight: true }
    RowLayout {
      Button { text: "Zurück"; enabled: wizard.step > 0; onClicked: wizard.step-- }
      Button { text: wizard.step === wizard.steps.length - 1 ? "Abschließen" : "Weiter"; onClicked: { if (wizard.step < wizard.steps.length - 1) wizard.step++; else { rampi.finishSetup(); wizard.close(); } } }
      Button { text: "Überspringen"; onClicked: wizard.close() }
    }
  }
}
