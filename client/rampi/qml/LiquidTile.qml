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
  signal activated()
  focusPolicy: Qt.StrongFocus
  Accessible.role: Accessible.Button
  Accessible.name: title
  Accessible.onPressAction: activated()
  onSelectedChanged: {
    if (selected && !reducedMotion) ripple.restart()
  }
  SequentialAnimation {
    id: ripple
    NumberAnimation { target: tile; property: "wave"; to: 24; duration: 65; easing.type: Easing.OutQuad }
    NumberAnimation { target: tile; property: "wave"; to: -5; duration: 55; easing.type: Easing.InOutQuad }
    NumberAnimation { target: tile; property: "wave"; to: 0; duration: 80; easing.type: Easing.OutQuad }
  }
  Shape {
    anchors.fill: parent
    anchors.margins: 5
    layer.enabled: false
    ShapePath {
      strokeWidth: 0
      fillColor: tile.selected ? Qt.lighter(tile.accent, 1.12) : tile.accent
      PathSvg {
        path: {
          let w = tile.width - 10, h = tile.height - 10, r = 28, v = tile.wave;
          return `M ${r} 0 C ${w*.35} ${v}, ${w*.65} ${-v}, ${w-r} 0 Q ${w} 0 ${w} ${r} C ${w-v} ${h*.35}, ${w+v} ${h*.65}, ${w} ${h-r} Q ${w} ${h} ${w-r} ${h} C ${w*.65} ${h-v}, ${w*.35} ${h+v}, ${r} ${h} Q 0 ${h} 0 ${h-r} C ${v} ${h*.65}, ${-v} ${h*.35}, 0 ${r} Q 0 0 ${r} 0 Z`;
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
      color: tile.darkInk ? "#111820" : "#ffffff"
    }
    Text {
      text: tile.subtitle; width: parent.width
      horizontalAlignment: Text.AlignHCenter; font.pixelSize: 17
      color: tile.darkInk ? "#1b242b" : "#edf3ff"
    }
  }
  Text {
    anchors { bottom: parent.bottom; bottomMargin: 27; horizontalCenter: parent.horizontalCenter }
    text: tile.caption; font.pixelSize: 10; font.letterSpacing: 2
    color: tile.darkInk ? "#1b242b" : "#e9f1ff"
  }
  MouseArea {
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
