import QtQuick

// Controlled slider: shows ``value`` and reports drags through ``moved``.
Item {
    id: root
    property real from: 0
    property real to: 100
    property real value: 0
    property var trackGradient: null
    signal moved(real value)

    implicitHeight: 22
    implicitWidth: 160
    readonly property real ratio: Math.max(0, Math.min(1, (value - from) / (to - from)))
    readonly property bool engaged: area.pressed || area.containsMouse

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        x: 8; width: parent.width - 16
        height: root.trackGradient ? 8 : 4; radius: height / 2
        color: Theme.hover
        gradient: root.trackGradient
        Rectangle {
            visible: !root.trackGradient
            width: parent.width * root.ratio; height: parent.height; radius: parent.radius
            color: Theme.accent
        }
    }
    Rectangle {
        id: knob
        width: 16; height: 16; radius: 8
        anchors.verticalCenter: parent.verticalCenter
        x: track.x + track.width * root.ratio - width / 2
        color: "#ffffff"
        border.width: root.trackGradient || !Theme.dark ? 1.5 : 0
        border.color: "#38000000"
        scale: area.pressed ? 1.25 : area.containsMouse ? 1.12 : 1
        Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
        Rectangle {
            anchors.centerIn: parent; z: -1
            width: 30; height: 30; radius: 15
            color: Theme.accent
            opacity: area.pressed ? 0.22 : 0
            Behavior on opacity { NumberAnimation { duration: 140 } }
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        function update(mouseX) {
            var ratio = Math.max(0, Math.min(1, (mouseX - track.x) / track.width))
            root.moved(root.from + ratio * (root.to - root.from))
        }
        onPressed: mouse => update(mouse.x)
        onPositionChanged: mouse => { if (pressed) update(mouse.x) }
        onWheel: wheel => {
            var step = (root.to - root.from) / 50 * (wheel.angleDelta.y > 0 ? 1 : -1)
            root.moved(Math.max(root.from, Math.min(root.to, root.value + step)))
        }
    }
}
