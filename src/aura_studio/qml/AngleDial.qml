import QtQuick

// Direction picker; 0° points right, angles grow clockwise like on screen.
Item {
    id: root
    property real value: 0
    signal moved(real value)
    implicitWidth: 46; implicitHeight: 46

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: area.containsMouse || area.pressed ? Theme.hover : Theme.raised
        border.width: 1
        border.color: Theme.stroke
        Behavior on color { ColorAnimation { duration: Theme.quick } }
    }
    Item {
        anchors.centerIn: parent
        width: parent.width; height: 2
        rotation: root.value
        Behavior on rotation { RotationAnimation { duration: 120; direction: RotationAnimation.Shortest } }
        Rectangle { x: parent.width / 2; width: parent.width / 2 - 7; height: 2; radius: 1; color: Theme.accent }
        Rectangle { x: parent.width - 13; y: -3; width: 8; height: 8; radius: 4; color: Theme.accent }
    }
    Rectangle { anchors.centerIn: parent; width: 5; height: 5; radius: 2.5; color: Theme.textDim }
    MouseArea {
        id: area
        anchors.fill: parent; anchors.margins: -4
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        function update(mouse) {
            var degrees = Math.atan2(mouse.y - height / 2, mouse.x - width / 2) * 180 / Math.PI
            root.moved((Math.round(degrees / 15) * 15 + 360) % 360)
        }
        onPressed: mouse => update(mouse)
        onPositionChanged: mouse => { if (pressed) update(mouse) }
    }
}
