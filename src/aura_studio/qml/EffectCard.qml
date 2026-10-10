import QtQuick

// Gallery tile: a still frame of the effect rendered on a tiny key grid.
Rectangle {
    id: root
    property var effect
    property bool selected: false
    signal clicked()

    implicitHeight: 112
    radius: Theme.radius
    color: selected ? Theme.raised : area.containsMouse ? Theme.raised : Theme.card
    border.width: selected ? 1.5 : 1
    border.color: selected ? Theme.accent : area.containsMouse ? Theme.stroke : Theme.strokeSoft
    scale: area.pressed ? 0.97 : 1
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on border.color { ColorAnimation { duration: Theme.smooth } }
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }

    KeyGrid {
        x: 10; y: 10
        width: parent.width - 20
        height: parent.height - 50
        cells: root.effect.thumb
    }
    Text {
        x: 14
        anchors.bottom: parent.bottom; anchors.bottomMargin: 12
        width: parent.width - 44
        text: root.effect.name
        color: root.selected ? Theme.text : Theme.textDim
        font.pixelSize: 13; font.weight: Font.DemiBold
        elide: Text.ElideRight
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }
    Rectangle {
        width: 18; height: 18; radius: 9
        anchors.right: parent.right; anchors.rightMargin: 12
        anchors.bottom: parent.bottom; anchors.bottomMargin: 11
        color: Theme.accent
        scale: root.selected ? 1 : 0
        Behavior on scale { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutBack } }
        Icon { anchors.centerIn: parent; name: "check"; size: 11; weight: 2.2; color: Theme.accentInk }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
