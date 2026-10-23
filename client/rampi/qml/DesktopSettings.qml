import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
  id: desktop
  property string output: ""
  readonly property var display: rampi.desktop.displays.find(function(d) { return d.name === output; }) || ({modes: [], current: ""})
  spacing: 12
  Label { text: "Anzeige, Tastatur & Maus"; font.pixelSize: 23; font.bold: true }
  Label { text: rampi.desktop.error; visible: text !== ""; textFormat: Text.PlainText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  RampiButton { text: "Anzeigen und Eingabe aktualisieren"; onClicked: rampi.refreshDesktop() }
  ComboBox { id: outputs; objectName: "displayOutput"; Layout.fillWidth: true; model: rampi.desktop.displays; textRole: "name"; valueRole: "name"; currentIndex: model.findIndex(function(d) { return d.name === desktop.output; }); displayText: currentIndex < 0 ? "Anzeige auswählen" : currentText; onActivated: desktop.output = currentValue }
  ComboBox { id: modes; objectName: "displayMode"; Layout.fillWidth: true; model: desktop.display.modes; currentIndex: model.indexOf(desktop.display.current) }
  RampiButton { text: "Auflösung übernehmen"; enabled: modes.currentIndex >= 0 && !rampi.desktop.busy; onClicked: { rollback.previousMode = desktop.display.current; rollback.output = desktop.output; rampi.applyDesktop(desktop.output, modes.currentText); rollback.open(); } }
  ComboBox { id: layout; objectName: "keyboardLayout"; Layout.fillWidth: true; model: rampi.desktop.layouts; textRole: "label"; valueRole: "key"; currentIndex: model.findIndex(function(k) { return k.key === rampi.desktop.layout; }) }
  RampiButton { text: "Tastaturlayout übernehmen"; enabled: layout.currentIndex >= 0 && !rampi.desktop.busy; onClicked: rampi.applyKeyboard(layout.currentValue) }
  RowLayout {
    Label { text: "Mausbeschleunigung" }
    SpinBox { id: speed; from: 1; to: 5; value: 2 }
    RampiButton { text: "Übernehmen"; enabled: !rampi.desktop.busy; onClicked: rampi.applyPointer(speed.value) }
  }
  Label { text: "Änderungen gelten für die laufende X11-Sitzung. Firmware und Bootkonfiguration bleiben erhalten. Bei einer neuen Auflösung wird nach 15 Sekunden automatisch zurückgestellt, falls du sie nicht bestätigst."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  FullPage {
    id: rollback
    title: "Ist die neue Auflösung gut lesbar?"
    property string previousMode: ""
    property string output: ""
    property int seconds: 15
    onOpened: { seconds = 15; countdown.start(); }
    onClosed: countdown.stop()
    onRejected: if (previousMode !== "") rampi.applyDesktop(output, previousMode)
    Timer { id: countdown; interval: 1000; repeat: true; onTriggered: { rollback.seconds--; if (rollback.seconds <= 0) rollback.reject(); } }
    contentItem: ColumnLayout {
      Label { text: "Automatisch zurück in " + rollback.seconds + " Sekunden" }
      RampiButton { text: "Auflösung behalten"; onClicked: rollback.accept() }
      RampiButton { text: "Zurückstellen"; onClicked: rollback.reject() }
      Item { Layout.fillHeight: true }
    }
  }
  onVisibleChanged: if (visible) rampi.refreshDesktop()
}
