import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Start page: every configurable device at a glance.
Item {
    id: page
    signal openDevice(string id)
    signal openOled()
    readonly property var others: service.devices.filter(device => !device.controllable)

    component Chip: Rectangle {
        property string label: ""
        property bool good: false
        implicitWidth: chipText.implicitWidth + 18; implicitHeight: 24
        radius: 12
        color: good ? Qt.rgba(Theme.good.r, Theme.good.g, Theme.good.b, 0.14) : Theme.raised
        border.width: 1
        border.color: Theme.strokeSoft
        Text {
            id: chipText
            anchors.centerIn: parent
            text: parent.label
            color: parent.good ? Theme.good : Theme.textDim
            font.pixelSize: 11; font.weight: Font.DemiBold
        }
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight + 48
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: column
            x: 24; y: 24
            width: Math.min(scroller.width - 48, 980)
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Layout.bottomMargin: 6
                Column {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: L.t("Übersicht"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
                    Text { text: service.status; color: Theme.textFaint; font.pixelSize: 12 }
                }
                PillButton { icon: "refresh"; text: L.t("Neu suchen"); onClicked: service.scan() }
            }

            Repeater {
                model: service.overview
                delegate: Rectangle {
                    id: card
                    Layout.fillWidth: true
                    implicitHeight: 132
                    radius: 20
                    color: cardArea.containsMouse ? Theme.raised : Theme.card
                    border.width: 1
                    border.color: cardArea.containsMouse ? Theme.stroke : Theme.strokeSoft
                    Behavior on color { ColorAnimation { duration: Theme.quick } }

                    MouseArea {
                        id: cardArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { Sfx.play("nav"); page.openDevice(modelData.id) }
                    }
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 18

                        // What the device is showing right now.
                        Item {
                            implicitWidth: 196; implicitHeight: 96
                            opacity: modelData.enabled ? 1 : 0.35
                            KeyGrid {
                                anchors.fill: parent
                                visible: modelData.kind === "keyboard"
                                radius: 12
                                cells: modelData.thumb
                            }
                            Rectangle {
                                anchors.fill: parent
                                visible: modelData.kind !== "keyboard"
                                radius: 12
                                color: "#0a0a0d"
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 34; height: 34; radius: 17
                                    color: modelData.thumb[Math.floor(modelData.thumb.length / 2)] || "#000000"
                                }
                                Icon { anchors.centerIn: parent; name: "mouse"; size: 62; weight: 1.1; color: "#40ffffff" }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: Theme.text
                                font.pixelSize: 18; font.weight: Font.Bold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.enabled
                                      ? modelData.effectName + L.t("  ·  Helligkeit ") + modelData.brightness + " %"
                                      : L.t("Beleuchtung aus")
                                color: Theme.textDim
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }
                            Flow {
                                Layout.fillWidth: true
                                Layout.topMargin: 4
                                spacing: 6
                                Chip { label: modelData.virtual ? L.t("Simulation") : L.t("Verbunden · ") + modelData.source; good: !modelData.virtual }
                                Chip { visible: modelData.battery >= 0; label: L.t("Akku ") + modelData.battery + " %" }
                                Chip { label: modelData.lamps > 1 ? modelData.lamps + L.t(" Tasten einzeln") : L.t("1 LED") }
                                Chip { visible: modelData.hasOled; label: L.t("OLED-Display") }
                            }
                        }
                        Column {
                            spacing: 10
                            Layout.alignment: Qt.AlignVCenter
                            Row {
                                anchors.right: parent.right
                                spacing: 10
                                Text {
                                    text: modelData.enabled ? L.t("An") : L.t("Aus")
                                    color: Theme.textFaint; font.pixelSize: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Toggle {
                                    checked: modelData.enabled
                                    onToggled: value => service.setDeviceEnabled(modelData.id, value)
                                }
                            }
                            Row {
                                anchors.right: parent.right
                                spacing: 8
                                PillButton {
                                    visible: modelData.hasOled
                                    icon: "display"; text: "OLED"; sound: "nav"
                                    implicitHeight: 34
                                    onClicked: page.openOled()
                                }
                                PillButton {
                                    primary: true
                                    text: L.t("Beleuchtung"); icon: "spark"; sound: "nav"
                                    implicitHeight: 34
                                    onClicked: page.openDevice(modelData.id)
                                }
                            }
                        }
                    }
                }
            }

            Text {
                visible: page.others.length > 0
                Layout.topMargin: 14
                text: L.t("ERKANNT, ABER NICHT STEUERBAR")
                color: Theme.textFaint
                font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
            }
            Repeater {
                model: page.others
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Rectangle {
                        implicitWidth: 36; implicitHeight: 36; radius: 11
                        color: Theme.card
                        border.width: 1
                        border.color: Theme.strokeSoft
                        Icon {
                            anchors.centerIn: parent
                            name: modelData.category === "Tastatur" ? "keyboard" : modelData.category === "Maus" ? "mouse" : "chip"
                            color: Theme.textFaint
                        }
                    }
                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        Text { text: modelData.name; color: Theme.textDim; font.pixelSize: 14 }
                        Text {
                            width: parent.width
                            text: [L.t(modelData.category), modelData.product_id, modelData.detail].filter(part => part !== "").join("  ·  ")
                            color: Theme.textFaint; font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
