import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal applied()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 18

        Column {
            Layout.fillWidth: true
            spacing: 3
            Text { text: L.t("Profile"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
            Text {
                text: L.t("Gespeicherte Lichtstimmungen. Ein Klick wendet sie auf das ausgewählte Gerät an.")
                color: Theme.textFaint; font.pixelSize: 12
            }
        }

        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: grid.implicitHeight + 8
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            Flow {
                id: grid
                width: scroller.width - 10
                spacing: 14
                readonly property int columns: Math.max(1, Math.floor((width + spacing) / 264))
                Repeater {
                    model: service.profiles
                    delegate: Rectangle {
                        id: card
                        width: (grid.width - (grid.columns - 1) * grid.spacing) / grid.columns
                        height: 176
                        radius: Theme.radius
                        readonly property bool active: service.activeProfile === modelData.file
                        property bool confirming: false
                        color: cardArea.containsMouse ? Theme.raised : Theme.card
                        border.width: active ? 1.5 : 1
                        border.color: active ? Theme.accent : cardArea.containsMouse ? Theme.stroke : Theme.strokeSoft
                        scale: cardArea.pressed ? 0.98 : 1
                        Behavior on color { ColorAnimation { duration: Theme.quick } }
                        Behavior on border.color { ColorAnimation { duration: Theme.smooth } }
                        Behavior on scale { NumberAnimation { duration: 110 } }

                        MouseArea {
                            id: cardArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (card.confirming) { card.confirming = false; return }
                                service.applyProfile(modelData.file)
                                page.applied()
                            }
                        }
                        KeyGrid {
                            x: 12; y: 12
                            width: parent.width - 24; height: 92
                            cells: modelData.thumb
                        }
                        Rectangle {
                            visible: card.active && !card.confirming
                            x: parent.width - width - 52
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 21
                            width: activeLabel.implicitWidth + 16; height: 22; radius: 11
                            color: Theme.accent
                            Text {
                                id: activeLabel
                                anchors.centerIn: parent
                                text: L.t("Aktiv")
                                color: Theme.accentInk
                                font.pixelSize: 11; font.weight: Font.Bold
                            }
                        }
                        Column {
                            x: 16
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 15
                            width: parent.width - 70
                            spacing: 3
                            opacity: card.confirming ? 0 : 1
                            Behavior on opacity { NumberAnimation { duration: Theme.quick } }
                            Text {
                                width: parent.width
                                text: modelData.name
                                color: Theme.text
                                font.pixelSize: 15; font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                text: modelData.effectName + "  ·  " + modelData.brightness + " %"
                                color: Theme.textFaint
                                font.pixelSize: 12
                            }
                        }
                        IconButton {
                            visible: !card.confirming
                            anchors.right: parent.right; anchors.rightMargin: 12
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 16
                            icon: "trash"; tip: L.t("Profil löschen"); flat: true; size: 32
                            onClicked: card.confirming = true
                        }
                        // Deleting asks once, right inside the card.
                        Row {
                            visible: card.confirming
                            x: 16
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 16
                            spacing: 8
                            Text {
                                text: L.t("Wirklich löschen?")
                                color: Theme.text
                                font.pixelSize: 13
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(0, card.width - 32 - 16 - yes.width - no.width)
                                elide: Text.ElideRight
                            }
                            PillButton { id: yes; text: L.t("Löschen"); danger: true; implicitHeight: 32; onClicked: service.deleteProfile(modelData.file) }
                            PillButton { id: no; text: L.t("Abbrechen"); implicitHeight: 32; onClicked: card.confirming = false }
                        }
                        Timer { interval: 6000; running: card.confirming; onTriggered: card.confirming = false }
                    }
                }
            }
            Column {
                visible: service.profiles.length === 0
                anchors.centerIn: parent
                spacing: 10
                Icon { name: "layers"; size: 36; color: Theme.textFaint; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    text: L.t("Noch keine Profile")
                    color: Theme.textDim; font.pixelSize: 15; font.weight: Font.DemiBold
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: L.t("Stelle im Studio einen Effekt ein und speichere ihn rechts unten als Profil.")
                    color: Theme.textFaint; font.pixelSize: 12
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
}
