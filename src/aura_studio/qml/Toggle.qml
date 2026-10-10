import QtQuick

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool value)

    implicitWidth: 40; implicitHeight: 23
    radius: height / 2
    color: checked ? Theme.accent : Theme.dark ? Theme.hover : "#c4c4d0"
    border.width: 1
    border.color: checked ? "transparent" : Theme.strokeSoft
    Behavior on color { ColorAnimation { duration: Theme.smooth } }

    Rectangle {
        width: 17; height: 17; radius: 8.5
        y: 3
        x: root.checked ? root.width - width - 3 : 3
        color: root.checked ? Theme.accentInk : Theme.dark ? Theme.textDim : "#ffffff"
        scale: area.pressed ? 0.86 : 1
        Behavior on x { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutBack; easing.overshoot: 1.4 } }
        Behavior on color { ColorAnimation { duration: Theme.smooth } }
        Behavior on scale { NumberAnimation { duration: 90 } }
    }
    MouseArea {
        id: area
        anchors.fill: parent; anchors.margins: -6
        cursorShape: Qt.PointingHandCursor
        onClicked: { Sfx.play(root.checked ? "toggle_off" : "toggle_on"); root.toggled(!root.checked) }
    }
}
