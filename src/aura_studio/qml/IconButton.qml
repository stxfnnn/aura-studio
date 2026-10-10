import QtQuick
import QtQuick.Controls

// Round icon-only button with a tooltip.
Rectangle {
    id: root
    property string icon: ""
    property string tip: ""
    property bool active: false
    property bool flat: false
    property real size: 34
    property string sound: "tap"
    signal clicked()

    implicitWidth: size; implicitHeight: size
    radius: size / 2
    color: active ? Theme.accentSoft : area.containsMouse ? Theme.hover : flat ? "transparent" : Theme.raised
    border.width: flat && !active ? 0 : 1
    border.color: active ? Theme.accentLine : Theme.strokeSoft
    scale: area.pressed ? 0.92 : 1
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    Icon {
        anchors.centerIn: parent
        name: root.icon; size: root.size * 0.47
        color: root.active ? Theme.accent : area.containsMouse ? Theme.text : Theme.textDim
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: { Sfx.play(root.sound); root.clicked() }
    }
    ToolTip.visible: tip !== "" && area.containsMouse
    ToolTip.delay: 500
    ToolTip.text: tip
}
