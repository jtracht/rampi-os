import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

Control {
  id: tile
  required property string title
  required property string subtitle
  required property string caption
  required property string symbol
  required property string iconFile
  required property color accent
  property bool selected: false
  property bool reducedMotion: false
  property bool darkInk: false
  property real wave: 0
  property real phase: 0
  property int startupDelay: 0
  hoverEnabled: true
  readonly property var shell: ApplicationWindow.window
  objectName: "liquid-" + iconFile
  scale: tileMouse.pressed ? 0.97 : 1
  Behavior on scale { NumberAnimation { duration: reducedMotion ? 0 : 120; easing.type: Easing.OutCubic } }
  function respond() { if (!reducedMotion) ripple.restart(); }
  onActiveFocusChanged: if (activeFocus) { respond(); if (shell) shell.feedback.selection(); }
  onHoveredChanged: if (hovered) { respond(); if (shell) shell.feedback.selection(); }
  onActivated: if (shell) shell.feedback.activate()
  Timer { interval: 40 + tile.startupDelay; running: true; onTriggered: tile.respond() }
  NumberAnimation on phase { from: 0; to: Math.PI * 2; duration: 2700; loops: Animation.Infinite; running: tile.visible && !tile.reducedMotion && (tile.selected || tile.hovered); easing.type: Easing.Linear }
  onReducedMotionChanged: if (reducedMotion) { ripple.stop(); wave = 0; phase = 0; }
  signal activated()
  focusPolicy: Qt.StrongFocus
  Accessible.role: Accessible.Button
  Accessible.name: title
  Accessible.onPressAction: activated()
  onSelectedChanged: {
    if (selected) respond()
  }
  SequentialAnimation {
    id: ripple
    NumberAnimation { target: tile; property: "wave"; to: 20; duration: 55; easing.type: Easing.OutQuad }
    NumberAnimation { target: tile; property: "wave"; to: -9; duration: 65; easing.type: Easing.InOutQuad }
    NumberAnimation { target: tile; property: "wave"; to: 0; duration: 100; easing.type: Easing.OutQuad }
  }
  Shape {
    anchors.fill: parent
    anchors.margins: 16
    layer.enabled: false
    ShapePath {
      strokeWidth: 0
      fillColor: tile.selected ? Qt.lighter(tile.accent, 1.12) : tile.accent
      PathSvg {
        path: {
          let w = tile.width - 32, h = tile.height - 32, r = 28;
          let idle = tile.reducedMotion ? 0 : (tile.selected || tile.hovered ? 4 : 0);
          let p = tile.phase, v = tile.wave;
          // Independent harmonics and unequal control points keep all four
          // edges moving without turning the tile into a symmetric breathing box.
          let a = v * .85 + idle * Math.sin(p);
          let b = -v * .55 + idle * Math.sin(p * 2 + 1.3);
          let c = v * .68 + idle * Math.sin(p + 3.8);
          let d = -v * .93 + idle * Math.cos(p * 3 + .6);
          return `M ${r} 0 C ${w*.23} ${a}, ${w*.71} ${b}, ${w-r} 0 Q ${w} 0 ${w} ${r} C ${w+c} ${h*.29}, ${w+d} ${h*.73}, ${w} ${h-r} Q ${w} ${h} ${w-r} ${h} C ${w*.68} ${h-b}, ${w*.31} ${h-a}, ${r} ${h} Q 0 ${h} 0 ${h-r} C ${-d} ${h*.64}, ${-c} ${h*.24}, 0 ${r} Q 0 0 ${r} 0 Z`;
        }
      }
    }
  }
  Column {
    anchors.centerIn: parent
    width: parent.width - 28
    spacing: 10
    Image {
      source: "../icons/" + tile.iconFile + ".svg"
      width: parent.width
      height: 100
      sourceSize: Qt.size(88, 88)
      fillMode: Image.PreserveAspectFit
    }
    Text {
      text: tile.title; width: parent.width
      horizontalAlignment: Text.AlignHCenter
      font.pixelSize: 23; font.weight: Font.DemiBold
      fontSizeMode: Text.HorizontalFit; minimumPixelSize: 18
      color: tile.darkInk ? "#111820" : "#ffffff"
    }
    Text {
      text: tile.subtitle; width: parent.width
      horizontalAlignment: Text.AlignHCenter; font.pixelSize: 17
      fontSizeMode: Text.HorizontalFit; minimumPixelSize: 13
      color: tile.darkInk ? "#1b242b" : "#edf3ff"
    }
  }
  Text {
    anchors { bottom: parent.bottom; bottomMargin: 27; horizontalCenter: parent.horizontalCenter }
    text: tile.caption; font.pixelSize: 10; font.letterSpacing: 2
    width: parent.width - 32; horizontalAlignment: Text.AlignHCenter
    fontSizeMode: Text.HorizontalFit; minimumPixelSize: 8
    color: tile.darkInk ? "#1b242b" : "#e9f1ff"
  }
  MouseArea {
    id: tileMouse
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onEntered: tile.forceActiveFocus()
    onClicked: tile.activated()
  }
  Keys.onReturnPressed: activated()
  Keys.onEnterPressed: activated()
  Keys.onSpacePressed: activated()
}
