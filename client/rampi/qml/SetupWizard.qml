import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

FullPage {
  id: wizard
  title: "Rampi einrichten"
  property int step: 0
  signal settingsRequested(int page)
  readonly property var steps: [
    {title: "Sprache & Tastatur", text: "Die Oberfläche dieses Entwicklungsstands ist deutsch. Die Systemsprache wird bei der Raspberry-Pi-Ersteinrichtung festgelegt. Die Eingabegeräte lassen sich in den Systemeinstellungen verwalten.", page: 1, label: "Tastatur und Maus"},
    {title: "HDMI-Anzeige", text: "Wähle eine gut lesbare Auflösung für Bildschirm oder Beamer. Rampi verändert keine Firmware- oder Bootoptionen.", page: 1, label: "Anzeige einstellen"},
    {title: "WLAN", text: "Suche und verbinde dein WLAN direkt im WLAN-Tab. NetworkManager verwaltet Verbindung und persönliche Zugangsdaten.", page: 2, label: "WLAN einrichten"},
    {title: "Bluetooth", text: "Suche und kopple Tastatur oder Maus in den Rampi-Einstellungen. BlueZ führt die Kopplung aus; Rampi zeigt PINs und Bestätigungen an. Kopplungen gelten für das ganze Gerät.", page: 3, label: "Geräte koppeln"},
    {title: "Linux-Konto & Login", text: "Du bist mit deinem persönlichen Linux-Systemkonto angemeldet. LightDM und PAM verwalten den Login. Zusätzliche normale Konten lassen sich über AccountsService mit polkit-Freigabe anlegen.", page: 1, label: "Linux-Konten"},
    {title: "VPN", text: "Wähle Tailscale oder WireGuard. Beachte die systemweiten Routingauswirkungen und die Berechtigungen anderer Benutzer.", page: 4, label: "VPN-Einstellungen"},
    {title: "Windows-Host", text: "Verwende einen eingeschalteten Windows-11-Pro-Laptop und dein eigenes Windows-Konto. Der Host-Installer prüft vorhandene Dienste vor Änderungen.", page: 0, label: "Host konfigurieren"},
    {title: "SSH-Schlüssel", text: "Erzeuge einen persönlichen Schlüssel. Übertrage nur den öffentlichen Teil auf Windows und prüfe den Host-Fingerprint unabhängig, bevor du ihn akzeptierst.", action: "ssh-key", label: "Schlüssel erzeugen"},
    {title: "Desktop-Streaming", text: "Sunshine teilt die aktive Windows-Konsole. Verwende für eine persönliche Windows-Anmeldung RDP. Kopple den Host für dein aktuelles Windows-Profil; die Kopplungsschlüssel bleiben getrennt.", action: "stream-pair", label: "Streaming-Host koppeln"},
    {title: "Remote Desktop", text: "FreeRDP verbindet mit Microsoft RDP. Kennwörter werden interaktiv abgefragt. Prüfe das Zertifikat vor dem ersten Vertrauen; Windows erlaubt nur eine interaktive Desktopsitzung.", module: "rdp", label: "RDP prüfen"},
    {title: "Kanban & Browser", text: "Richte eine lokale JSON-Datei oder einen lesenden Cloud-Connector ein. Cloud-Zugänge sind noch nicht gegen persönliche Konten validiert. Dein Browser verwendet ein eigenes Profil.", page: 5, label: "Datenquellen einrichten"},
    {title: "Abschlussdiagnose", text: "Prüfe die tatsächlich installierten Programme. Eine erfolgreiche Diagnose bestätigt keine noch nicht durchgeführten Hardware- oder Verbindungstests. Du kannst alle Einstellungen später ändern.", action: "diagnostics", label: "Diagnose anzeigen"}
  ]
  contentItem: ColumnLayout {
    spacing: 24
    Label { text: (wizard.step + 1) + " / " + wizard.steps.length; opacity: 0.65 }
    ProgressBar { from: 0; to: wizard.steps.length; value: wizard.step + 1; Layout.fillWidth: true }
    Label { text: wizard.steps[wizard.step].title; font.pixelSize: 30; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Label { text: wizard.steps[wizard.step].text; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 17; lineHeight: 1.5 }
    RampiButton {
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
      RampiButton { text: "Zurück"; enabled: wizard.step > 0; onClicked: wizard.step-- }
      RampiButton { text: wizard.step === wizard.steps.length - 1 ? "Abschließen" : "Weiter"; onClicked: { if (wizard.step < wizard.steps.length - 1) wizard.step++; else { rampi.finishSetup(); wizard.close(); } } }
      RampiButton { text: "Überspringen"; onClicked: wizard.close() }
    }
  }
}
