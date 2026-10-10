import QtQuick

// Short status message that slides in at the bottom.
Rectangle {
    id: root
    property string kind: "info"
    function show(text, messageKind) {
        label.text = text
        kind = messageKind || "info"
        shown = true
        timer.restart()
    }
    property bool shown: false

    width: Math.min(row.implicitWidth + 36, parent.width - 40)
    height: 44
    radius: 22
    color: Theme.popup
    border.width: 1
    border.color: kind === "error" ? Qt.rgba(1, 0.42, 0.5, 0.6) : Theme.stroke
    anchors.horizontalCenter: parent.horizontalCenter
    y: shown ? parent.height - height - 26 : parent.height + 10
    opacity: shown ? 1 : 0
    Behavior on y { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: 220 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 10
        Rectangle {
            width: 8; height: 8; radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: root.kind === "error" ? Theme.bad : root.kind === "success" ? Theme.good : Theme.accent
        }
        Text {
            id: label
            color: Theme.text
            font.pixelSize: 13
            width: Math.min(implicitWidth, root.parent.width - 100)
            elide: Text.ElideRight
        }
    }
    Timer { id: timer; interval: 3200; onTriggered: root.shown = false }
}
