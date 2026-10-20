import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
  id: root
  parent: Overlay.overlay
  anchors.fill: parent
  visible: false
  implicitWidth: 0
  implicitHeight: 0
  padding: Math.max(24, Math.min(width * 0.05, 80))
  property string title: "Rampi"
  property int standardButtons: 0
  property var previousFocus: null
  readonly property var shell: ApplicationWindow.window
  readonly property bool current: shell && shell.navigationStack.length > 0 && shell.navigationStack[shell.navigationStack.length - 1] === root
  enabled: current
  z: shell ? shell.navigationStack.indexOf(root) + 10 : 10
  signal opened()
  signal closed()
  signal accepted()
  signal rejected()
  function open() {
    if (current) return;
    previousFocus = shell.activeFocusItem;
    shell.navigationStack = shell.navigationStack.filter(function(p) { return p !== root; }).concat([root]);
    visible = true;
    forceActiveFocus();
    opened();
  }
  function close() {
    if (!visible) return;
    visible = false;
    shell.navigationStack = shell.navigationStack.filter(function(p) { return p !== root; });
    closed();
    if (previousFocus && previousFocus.visible) previousFocus.forceActiveFocus();
  }
  function accept() { close(); accepted(); }
  function reject() { close(); rejected(); }
  Shortcut { sequence: "Escape"; enabled: root.current; onActivated: root.reject() }
  background: Rectangle {
    color: "#080f16"
    MouseArea { anchors.fill: parent }
  }
  topPadding: header.height + padding
  bottomPadding: footer.height + status.height + padding + 12
  RowLayout {
    id: header
    parent: root
    x: root.padding; y: root.padding; width: root.width - 2 * root.padding
    RampiButton { text: "← Zurück"; onClicked: root.reject() }
    Label { text: root.title; font.pixelSize: 26; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
  }
  RowLayout {
    id: footer
    parent: root
    x: root.padding; y: root.height - root.padding - height - status.height - 12
    visible: root.standardButtons !== 0
    height: visible ? implicitHeight : 0
    RampiButton { visible: (root.standardButtons & Dialog.No) !== 0; text: "Abbrechen"; onClicked: root.reject() }
    RampiButton { visible: (root.standardButtons & Dialog.Yes) !== 0; text: "Bestätigen"; onClicked: root.accept() }
    RampiButton { visible: (root.standardButtons & (Dialog.Ok | Dialog.Close)) !== 0; text: "Zurück"; onClicked: root.close() }
  }
  RowLayout {
    id: status
    parent: root
    x: root.padding; y: root.height - root.padding - height
    width: root.width - root.padding * 2
    visible: shell && shell.lastMessage !== ""
    height: visible ? implicitHeight : 0
    Label { text: root.shell ? root.shell.lastMessage : ""; textFormat: Text.PlainText; Layout.fillWidth: true; elide: Text.ElideRight; maximumLineCount: 2; wrapMode: Text.WordWrap; color: "#9eb6c8" }
    RampiButton { text: "Details"; onClicked: root.shell.showMessageDetails() }
  }
  opacity: visible ? 1 : 0
  Behavior on opacity { NumberAnimation { duration: rampi.configuration.reduce_motion ? 0 : 160 } }
}
