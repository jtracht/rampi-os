import QtQuick
import QtQuick.Controls

TabButton {
  id: tab
  hoverEnabled: true
  readonly property var shell: ApplicationWindow.window
  onHoveredChanged: if (hovered && shell) shell.feedback.selection()
  onActiveFocusChanged: if (activeFocus && shell) shell.feedback.selection()
  onClicked: if (shell) shell.feedback.activate()
  padding: 14
  palette.buttonText: checked ? "#ffffff" : "#a9bdcc"
  background: Rectangle {
    radius: 10
    color: tab.checked ? "#12538a" : tab.hovered || tab.activeFocus ? "#2e4657" : "#152532"
    Behavior on color { ColorAnimation { duration: rampi.configuration.reduce_motion ? 0 : 120 } }
  }
}
