import QtQuick

// Still frame of an effect on a tiny key grid (13 columns).
Rectangle {
    id: root
    property var cells: []
    radius: 10
    color: "#0a0a0d"
    Grid {
        id: grid
        anchors.centerIn: parent
        columns: 13
        readonly property real cell: Math.min((root.width - 14) / 13, (root.height - 12) / 5)
        Repeater {
            model: root.cells
            delegate: Item {
                width: grid.cell; height: grid.cell
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: Math.max(0.6, grid.cell * 0.09)
                    radius: grid.cell * 0.24
                    color: modelData
                }
            }
        }
    }
}
