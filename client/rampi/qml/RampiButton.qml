import QtQuick
import QtQuick.Controls

Button {
  id: button
  padding: 12
  background: Rectangle {
    radius: 10
    color: !button.enabled ? "#17242e" : button.down ? "#3c647c" : button.hovered || button.activeFocus ? "#32556d" : "#203746"
    Behavior on color { ColorAnimation { duration: rampi.configuration.reduce_motion ? 0 : 120 } }
  }
  hoverEnabled: true
  readonly property var shell: ApplicationWindow.window
  onHoveredChanged: if (hovered && enabled && shell) shell.feedback.selection()
  onActiveFocusChanged: if (activeFocus && enabled && shell) shell.feedback.selection()
  onClicked: if (enabled && shell) shell.feedback.activate()
  scale: down ? 0.96 : hovered || activeFocus ? 1.025 : 1
  Behavior on scale { NumberAnimation { duration: rampi.configuration.reduce_motion ? 0 : 130; easing.type: Easing.OutCubic } }
  // Qt's platform theme can reserve button activation for Space. Rampi also
  // promises Enter; keep Qt rendering, focus, accessibility and Space handling.
  Keys.onReturnPressed: function(event) { if (!event.isAutoRepeat) clicked(); }
  Keys.onEnterPressed: function(event) { if (!event.isAutoRepeat) clicked(); }
}
