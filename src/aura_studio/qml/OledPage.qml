import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

// Compose content for the keyboard's OLED and store it in the keyboard.
Item {
    id: page
    readonly property var draft: oled.draft
    readonly property var frames: oled.preview
    property int frameIndex: 0
    onFramesChanged: frameIndex = 0

    Timer {
        running: page.visible && page.frames.length > 1
        repeat: true
        interval: page.frames.length ? Math.max(20, page.frames[page.frameIndex % page.frames.length].ms) : 100
        onTriggered: page.frameIndex = (page.frameIndex + 1) % page.frames.length
    }
    FileDialog {
        id: fileDialog
        title: L.t("Bild oder Animation wählen")
        nameFilters: [L.t("Bilder und Animationen (*.gif *.png *.jpg *.jpeg *.bmp *.webp *.svg)"), L.t("Alle Dateien (*)")]
        onAccepted: oled.openFile(selectedFile)
    }

    component Label: Text {
        color: Theme.textFaint
        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
    }
    component Row2: RowLayout {
        property string title: ""
        default property alias control: slot.data
        Layout.fillWidth: true
        spacing: 16
        Text { text: title; color: Theme.text; font.pixelSize: 14; Layout.fillWidth: true }
        Row { id: slot; spacing: 10 }
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
            width: Math.min(scroller.width - 48, 900)
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Column {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: L.t("OLED-Display"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
                    Text {
                        width: parent.width
                        text: oled.deviceName + L.t("  ·  Der Inhalt wird in der Tastatur gespeichert und läuft dort auch ohne Aura Studio weiter.")
                        color: Theme.textFaint; font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }
                // Shows the state this app set last; the keyboard cannot be asked.
                Text {
                    text: page.draft.power ? L.t("Display an") : L.t("Display aus")
                    color: Theme.textFaint; font.pixelSize: 12
                }
                IconButton {
                    icon: "power"; size: 40
                    active: page.draft.power
                    tip: page.draft.power ? L.t("Display ausschalten") : L.t("Display einschalten")
                    sound: page.draft.power ? "toggle_off" : "toggle_on"
                    onClicked: if (!oled.busy) oled.setPower(!page.draft.power)
                }
            }

            // ------------------------------------------------------- preview
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: screen.height + 86
                radius: 22
                color: Theme.well
                border.width: 1
                border.color: Theme.strokeSoft

                Rectangle {
                    id: screen
                    readonly property real factor: Math.max(1, Math.min(3, Math.floor((parent.width - 80) / 208)))
                    width: 208 * factor + 20; height: 64 * factor + 20
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 28
                    radius: 12
                    color: "#000000"
                    border.width: 1
                    border.color: Theme.stroke
                    Image {
                        anchors.centerIn: parent
                        width: 208 * screen.factor; height: 64 * screen.factor
                        source: page.frames.length ? page.frames[page.frameIndex % page.frames.length].src : ""
                        smooth: false
                        cache: false
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 18
                    text: oled.error !== "" ? oled.error : oled.info
                    color: oled.error !== "" ? "#ff6b81" : "#7a7a89"
                    font.pixelSize: 12
                }
            }

            // -------------------------------------------------------- source
            Segmented {
                options: [{value: "animation", label: L.t("Animation")}, {value: "file", label: L.t("Bild / GIF")},
                          {value: "text", label: L.t("Text")}]
                value: page.draft.source
                onChosen: value => oled.set("source", value)
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: options.implicitHeight + 40
                radius: Theme.radius
                color: Theme.card
                border.width: 1
                border.color: Theme.strokeSoft

                ColumnLayout {
                    id: options
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 16

                    // Animation
                    Label { text: L.t("MITGELIEFERTE ANIMATIONEN"); visible: page.draft.source === "animation" }
                    Flow {
                        id: animationFlow
                        Layout.fillWidth: true
                        visible: page.draft.source === "animation"
                        spacing: 10
                        readonly property int columns: Math.max(2, Math.floor((width + spacing) / 190))
                        Repeater {
                            model: oled.animations
                            delegate: Rectangle {
                                width: (animationFlow.width - (animationFlow.columns - 1) * animationFlow.spacing) / animationFlow.columns
                                height: width * 64 / 208 + 40
                                radius: 12
                                readonly property bool selected: page.draft.animation === modelData.id
                                color: tileArea.containsMouse || selected ? Theme.raised : Theme.panel
                                border.width: selected ? 1.5 : 1
                                border.color: selected ? Theme.accent : Theme.strokeSoft
                                Behavior on border.color { ColorAnimation { duration: Theme.smooth } }
                                Rectangle {
                                    x: 8; y: 8
                                    width: parent.width - 16; height: width * 64 / 208
                                    radius: 6
                                    color: "#000000"
                                    Image { anchors.fill: parent; anchors.margins: 2; source: modelData.src; smooth: true }
                                }
                                Text {
                                    x: 10
                                    anchors.bottom: parent.bottom; anchors.bottomMargin: 9
                                    text: modelData.name
                                    color: parent.selected ? Theme.text : Theme.textDim
                                    font.pixelSize: 13; font.weight: Font.DemiBold
                                }
                                MouseArea {
                                    id: tileArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (!parent.selected) { Sfx.play("select"); oled.set("animation", modelData.id) }
                                }
                            }
                        }
                    }

                    // File
                    Row2 {
                        visible: page.draft.source === "file"
                        title: oled.fileName !== "" ? oled.fileName : L.t("Keine Datei gewählt")
                        PillButton { icon: "plus"; text: L.t("Datei wählen …"); onClicked: fileDialog.open() }
                    }
                    Row2 {
                        visible: page.draft.source === "file"
                        title: L.t("Anpassung")
                        Segmented {
                            options: [{value: "fit", label: L.t("Einpassen")}, {value: "fill", label: L.t("Füllen")}, {value: "stretch", label: L.t("Strecken")}]
                            value: page.draft.mode
                            onChosen: value => oled.set("mode", value)
                        }
                    }
                    Row2 {
                        visible: page.draft.source === "file"
                        title: L.t("Längste Animation")
                        Segmented {
                            options: [{value: 16, label: L.t("16 Bilder")}, {value: 32, label: "32"}, {value: 64, label: "64"}, {value: 128, label: "128"}]
                            value: page.draft.maxFrames
                            onChosen: value => oled.set("maxFrames", value)
                        }
                    }

                    // Text
                    Rectangle {
                        visible: page.draft.source === "text"
                        Layout.fillWidth: true
                        implicitHeight: 42; radius: 21
                        color: Theme.panel
                        border.width: 1
                        border.color: textField.activeFocus ? Theme.accentLine : Theme.strokeSoft
                        TextInput {
                            id: textField
                            anchors.fill: parent
                            anchors.leftMargin: 16; anchors.rightMargin: 16
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.text
                            selectionColor: Theme.accent
                            selectedTextColor: Theme.accentInk
                            font.pixelSize: 14
                            maximumLength: 200
                            selectByMouse: true
                            clip: true
                            Component.onCompleted: text = page.draft.text
                            onTextEdited: oled.set("text", text)
                        }
                    }
                    Row2 {
                        visible: page.draft.source === "text"
                        title: L.t("Schriftgröße")
                        ValueSlider {
                            width: 220
                            anchors.verticalCenter: parent.verticalCenter
                            from: 10; to: 60
                            value: page.draft.size
                            onMoved: value => oled.set("size", Math.round(value))
                        }
                    }
                    Row2 {
                        visible: page.draft.source === "text"
                        title: L.t("Fett")
                        Toggle { checked: page.draft.bold; onToggled: value => oled.set("bold", value) }
                    }
                    Row2 {
                        visible: page.draft.source === "text"
                        title: L.t("Lauftext")
                        Toggle { checked: page.draft.scroll; onToggled: value => oled.set("scroll", value) }
                    }
                    Row2 {
                        visible: page.draft.source === "text" && page.draft.scroll
                        title: L.t("Geschwindigkeit")
                        ValueSlider {
                            width: 220
                            anchors.verticalCenter: parent.verticalCenter
                            value: page.draft.speed
                            onMoved: value => oled.set("speed", Math.round(value))
                        }
                    }

                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.strokeSoft }
                    Row2 {
                        title: L.t("Invertieren")
                        Toggle { checked: page.draft.invert; onToggled: value => oled.set("invert", value) }
                    }
                    Row2 {
                        title: L.t("Helligkeit  ·  ") + page.draft.brightness + " %"
                        ValueSlider {
                            width: 220
                            anchors.verticalCenter: parent.verticalCenter
                            from: 10; to: 100
                            value: page.draft.brightness
                            onMoved: value => oled.set("brightness", Math.round(value / 5) * 5)
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: L.t("Die Helligkeit wird in den Inhalt eingerechnet und gilt ab der nächsten Übertragung.")
                        color: Theme.textFaint; font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                }
            }

            // -------------------------------------------------------- upload
            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                PillButton {
                    primary: true
                    icon: "arrow"
                    text: oled.busy ? L.t("Wird übertragen …") : L.t("Auf Display übertragen")
                    enabled: !oled.busy && oled.error === ""
                    implicitHeight: 42
                    onClicked: oled.upload()
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 6; radius: 3
                    color: Theme.hover
                    opacity: oled.busy ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.smooth } }
                    Rectangle {
                        width: parent.width * oled.progress; height: parent.height; radius: 3
                        color: Theme.accent
                        Behavior on width { NumberAnimation { duration: 180 } }
                    }
                }
                Text {
                    visible: oled.busy
                    text: Math.round(oled.progress * 100) + " %"
                    color: Theme.textDim; font.pixelSize: 12
                }
            }
            Text {
                Layout.fillWidth: true
                text: L.t("Während der Übertragung pausiert die Tastenbeleuchtung. Bitte die Tastatur dabei nicht ausschalten.")
                color: Theme.textFaint; font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            // --------------------------------------------------- idle timeout
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 8
                visible: service.oledOptions.canIdle === true
                implicitHeight: idleBox.implicitHeight + 40
                radius: Theme.radius
                color: Theme.card
                border.width: 1
                border.color: Theme.strokeSoft
                RowLayout {
                    id: idleBox
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 16
                    Rectangle {
                        implicitWidth: 40; implicitHeight: 40; radius: 12
                        color: Theme.raised
                        Icon { anchors.centerIn: parent; name: "moon"; size: 20; color: service.oledOptions.oledIdle ? Theme.accent : Theme.textDim }
                    }
                    Column {
                        Layout.fillWidth: true
                        spacing: 3
                        Text { text: L.t("Display aus nach Inaktivität (Minuten)"); color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text {
                            width: parent.width
                            text: L.t("Schaltet das Display aus, wenn die Tastatur so lange nicht benutzt wurde, und beim nächsten Tastendruck wieder ein. Gilt, solange Aura Studio läuft.")
                            color: Theme.textFaint; font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }
                    }
                    Segmented {
                        options: [{value: 0, label: L.t("Nie")}, {value: 1, label: "1"}, {value: 5, label: "5"}, {value: 15, label: "15"}, {value: 30, label: "30"}, {value: 60, label: "60"}]
                        value: service.oledOptions.oledIdle || 0
                        onChosen: value => service.setDeviceOption("oledIdle", value)
                    }
                }
            }

            // ---------------------------------------------------- live clock
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: clockBox.implicitHeight + 40
                radius: Theme.radius
                color: Theme.card
                border.width: 1
                border.color: Theme.strokeSoft
                RowLayout {
                    id: clockBox
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 16
                    Rectangle {
                        implicitWidth: 40; implicitHeight: 40; radius: 12
                        color: Theme.raised
                        Icon { anchors.centerIn: parent; name: "clock"; size: 20; color: oled.clock ? Theme.accent : Theme.textDim }
                    }
                    Column {
                        Layout.fillWidth: true
                        spacing: 3
                        Text { text: L.t("Live-Uhr"); color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text {
                            width: parent.width
                            text: L.t("Zeigt Datum und Uhrzeit mit Sekunden an. Die Tastatur zählt nicht selbst weiter, deshalb läuft die Uhr nur, solange Aura Studio geöffnet ist. Zum Zurückwechseln erneut einen Inhalt übertragen oder eine Werksanimation wählen.")
                            color: Theme.textFaint; font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }
                    }
                    Toggle { checked: oled.clock; onToggled: value => oled.setClock(value) }
                }
            }

            // ------------------------------------------------------ firmware
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: firmware.implicitHeight + 40
                radius: Theme.radius
                color: Theme.card
                border.width: 1
                border.color: Theme.strokeSoft
                ColumnLayout {
                    id: firmware
                    x: 20; y: 20
                    width: parent.width - 40
                    spacing: 12
                    Text { text: L.t("Werksanimationen von ASUS"); color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Text {
                        Layout.fillWidth: true
                        text: L.t("Sechs Animationen sind ab Werk fest in der Tastatur gespeichert – dieselben, die Armoury Crate als Standard anbietet. ")
                              + L.t("Ein Klick schaltet sofort darauf um, ohne Übertragung. Wie sie aussehen, zeigt nur das Display selbst; eine Vorschau gibt es hier nicht. ")
                              + L.t("Dein eigener Inhalt erscheint wieder, sobald du ihn erneut überträgst.")
                        color: Theme.textFaint; font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.topMargin: 2
                        spacing: 8
                        Repeater {
                            model: oled.presetCount
                            delegate: PillButton {
                                text: L.t("Werk ") + (index + 1)
                                enabled: !oled.busy
                                onClicked: oled.selectPreset(index)
                            }
                        }
                    }
                }
            }
        }
    }
}
