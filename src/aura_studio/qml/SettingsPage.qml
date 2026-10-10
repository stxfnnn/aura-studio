import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    property string logText: ""
    property var picker: null
    readonly property var settings: service.settings

    Connections {
        target: service
        function onLogsChanged(text) { page.logText = text }
    }

    component Card: Rectangle {
        default property alias content: inner.data
        property string title: ""
        Layout.fillWidth: true
        implicitHeight: inner.implicitHeight + 40
        radius: Theme.radius
        color: Theme.card
        border.width: 1
        border.color: Theme.strokeSoft
        ColumnLayout {
            id: inner
            x: 20; y: 20
            width: parent.width - 40
            spacing: 16
        }
    }
    component CardTitle: Text {
        color: Theme.textFaint
        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
    }
    component SettingRow: RowLayout {
        property string title: ""
        property string hint: ""
        default property alias control: slot.data
        Layout.fillWidth: true
        spacing: 16
        Column {
            Layout.fillWidth: true
            spacing: 3
            Text { text: title; color: Theme.text; font.pixelSize: 14 }
            Text {
                visible: hint !== ""
                width: parent.width
                text: hint; color: Theme.textFaint; font.pixelSize: 12
                wrapMode: Text.Wrap
            }
        }
        Row { id: slot; spacing: 10; Layout.alignment: Qt.AlignVCenter }
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
            width: Math.min(scroller.width - 48, 860)
            spacing: 16

            Text { text: L.t("Einstellungen"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }

            Card {
                CardTitle { text: L.t("DARSTELLUNG") }
                SettingRow {
                    title: L.t("Sprache")
                    hint: L.t("„System“ richtet sich nach der Sprache deines Desktops.")
                    Segmented {
                        options: [{value: "system", label: L.t("System")}, {value: "de", label: "Deutsch"}, {value: "en", label: "English"}]
                        value: page.settings.language
                        onChosen: value => service.setSetting("language", value)
                    }
                }
                SettingRow {
                    title: L.t("Erscheinungsbild")
                    hint: L.t("„System“ folgt der Einstellung deines Desktops.")
                    Segmented {
                        options: [{value: "dark", label: L.t("Dunkel")}, {value: "light", label: L.t("Hell")}, {value: "system", label: L.t("System")}]
                        value: page.settings.theme
                        onChosen: value => service.setSetting("theme", value)
                    }
                }
                SettingRow {
                    title: L.t("Akzentfarbe")
                    hint: L.t("Färbt Schaltflächen, Regler und Markierungen.")
                    Segmented {
                        options: [{value: "effect", label: L.t("Folgt dem Effekt")}, {value: "custom", label: L.t("Eigene Farbe")}]
                        value: page.settings.accentMode
                        onChosen: value => service.setSetting("accentMode", value)
                    }
                    Rectangle {
                        id: accentChip
                        width: 34; height: 34; radius: 17
                        color: page.settings.accentColor
                        border.width: 2
                        border.color: Theme.stroke
                        opacity: page.settings.accentMode === "custom" ? 1 : 0.35
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                Sfx.play("tap")
                                service.setSetting("accentMode", "custom")
                                page.picker.openFor(accentChip, page.settings.accentColor, value => service.setSetting("accentColor", value))
                            }
                        }
                    }
                }
            }

            Card {
                CardTitle { text: L.t("KLANG") }
                SettingRow {
                    title: L.t("Bedienklänge")
                    hint: L.t("Leise Töne beim Klicken, Umschalten und Speichern.")
                    Toggle { checked: page.settings.sounds; onToggled: value => service.setSetting("sounds", value) }
                }
                SettingRow {
                    title: L.t("Lautstärke")
                    opacity: page.settings.sounds ? 1 : 0.4
                    ValueSlider {
                        width: 200
                        anchors.verticalCenter: parent.verticalCenter
                        value: page.settings.volume
                        onMoved: value => service.setSetting("volume", Math.round(value))
                    }
                    PillButton { text: L.t("Testen"); sound: "success"; implicitHeight: 32 }
                }
            }

            Card {
                CardTitle { text: L.t("BELEUCHTUNG") }
                SettingRow {
                    title: L.t("Geräte koppeln")
                    hint: L.t("Effekt und Farben gelten für alle Geräte gleichzeitig.")
                    Toggle { checked: page.settings.linked; onToggled: value => service.setSetting("linked", value) }
                }
                SettingRow {
                    title: L.t("Bei OLED-Übertragung alle Geräte pausieren")
                    hint: L.t("Hält auch die Beleuchtung der Maus an, solange Inhalte ans Display gesendet werden. Kann die Übertragung etwas beschleunigen, weil der Empfänger dann nur für das Display funkt.")
                    Toggle { checked: page.settings.oledPauseAll; onToggled: value => service.setSetting("oledPauseAll", value) }
                }
                SettingRow {
                    title: L.t("Bildrate")
                    hint: L.t("Mehr Bilder pro Sekunde wirken flüssiger, belasten aber die Funkverbindung stärker.")
                    Segmented {
                        options: [{value: 15, label: L.t("Sparsam")}, {value: 24, label: L.t("Ausgewogen")}, {value: 30, label: L.t("Flüssig")}]
                        value: page.settings.fps
                        onChosen: value => service.setSetting("fps", value)
                    }
                }
                SettingRow {
                    title: L.t("Tastaturlayout")
                    hint: L.t("Bestimmt Beschriftung und Tastenform in der Vorschau.")
                    Segmented {
                        options: [{value: "de", label: L.t("Deutsch (ISO)")}, {value: "us", label: L.t("US (ANSI)")}]
                        value: page.settings.layout
                        onChosen: value => service.setSetting("layout", value)
                    }
                }
            }

            Card {
                CardTitle { text: L.t("AKKU") }
                SettingRow {
                    title: L.t("Bei schwachem Akku benachrichtigen")
                    hint: L.t("Zeigt eine Systembenachrichtigung, sobald Tastatur oder Maus unter die Schwelle fallen. In der App werden sie immer markiert.")
                    Toggle { checked: page.settings.batteryAlerts; onToggled: value => service.setSetting("batteryAlerts", value) }
                }
                SettingRow {
                    title: L.t("Warnschwelle  ·  ") + page.settings.batteryThreshold + " %"
                    ValueSlider {
                        width: 200
                        anchors.verticalCenter: parent.verticalCenter
                        from: 5; to: 50
                        value: page.settings.batteryThreshold
                        onMoved: value => service.setSetting("batteryThreshold", Math.round(value / 5) * 5)
                    }
                }
            }

            Card {
                CardTitle { text: L.t("VERHALTEN") }
                SettingRow {
                    title: L.t("Beim Anmelden automatisch starten")
                    hint: L.t("Startet Aura Studio mit dem Desktop, damit Beleuchtung und Makros sofort laufen. Ist „Im Hintergrund weiterlaufen“ aktiv, startet es unauffällig im Systemabschnitt.")
                    Toggle { checked: service.autostart; onToggled: value => service.setAutostart(value) }
                }
                SettingRow {
                    title: L.t("Im Hintergrund weiterlaufen")
                    hint: L.t("Beim Schließen des Fensters bleibt Aura Studio im Systemabschnitt der Kontrollleiste aktiv, damit die Effekte weiterlaufen.")
                    Toggle { checked: page.settings.tray; onToggled: value => service.setSetting("tray", value) }
                }
                SettingRow {
                    title: L.t("Beim Beenden an die Firmware übergeben")
                    hint: L.t("Die Tastatur wechselt auf den ähnlichsten eingebauten Effekt, statt beim letzten Bild stehen zu bleiben.")
                    Toggle { checked: page.settings.fallback; onToggled: value => service.setSetting("fallback", value) }
                }
            }

            Card {
                RowLayout {
                    Layout.fillWidth: true
                    CardTitle { text: L.t("ERKANNTE HARDWARE"); Layout.fillWidth: true }
                    PillButton { icon: "refresh"; text: L.t("Neu suchen"); implicitHeight: 32; onClicked: service.scan() }
                }
                Repeater {
                    model: service.devices
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Rectangle {
                            implicitWidth: 36; implicitHeight: 36; radius: 11
                            color: Theme.raised
                            Icon {
                                anchors.centerIn: parent
                                name: modelData.category === "Tastatur" ? "keyboard" : modelData.category === "Maus" ? "mouse" : "chip"
                                color: modelData.controllable ? Theme.accent : Theme.textFaint
                            }
                        }
                        Column {
                            Layout.fillWidth: true
                            spacing: 2
                            Text { text: modelData.name; color: Theme.text; font.pixelSize: 14 }
                            Text {
                                width: parent.width
                                text: [L.t(modelData.category), modelData.product_id, modelData.detail].filter(part => part !== "").join("  ·  ")
                                color: Theme.textFaint; font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                        Rectangle {
                            implicitWidth: badge.implicitWidth + 18; implicitHeight: 24; radius: 12
                            color: modelData.controllable ? Qt.rgba(0.37, 0.88, 0.64, 0.12) : Theme.raised
                            Text {
                                id: badge
                                anchors.centerIn: parent
                                text: modelData.virtual ? L.t("Simulation") : modelData.controllable ? L.t("Steuerbar") : L.t("Kein Adapter")
                                color: modelData.controllable ? Theme.good : Theme.textFaint
                                font.pixelSize: 11; font.weight: Font.DemiBold
                            }
                        }
                    }
                }
            }

            Card {
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    CardTitle { text: L.t("DIAGNOSEPROTOKOLL"); Layout.fillWidth: true }
                    PillButton { icon: "refresh"; text: L.t("Laden"); implicitHeight: 32; onClicked: service.refreshLogs() }
                    PillButton { icon: "copy"; text: L.t("Kopieren"); implicitHeight: 32; onClicked: service.copyLogs() }
                }
                Text {
                    Layout.fillWidth: true
                    text: service.logLocation() + L.t("  ·  Seriennummern werden nicht protokolliert.")
                    color: Theme.textFaint; font.pixelSize: 12
                    elide: Text.ElideMiddle
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 280
                    visible: page.logText !== ""
                    radius: 10
                    color: Theme.well
                    border.width: 1
                    border.color: Theme.strokeSoft
                    Flickable {
                        id: logScroller
                        anchors.fill: parent
                        anchors.margins: 12
                        contentWidth: width
                        contentHeight: logView.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                        TextEdit {
                            id: logView
                            width: logScroller.width - 10
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.WrapAnywhere
                            text: page.logText
                            color: "#a9c2b0"
                            selectionColor: Theme.accent
                            selectedTextColor: Theme.accentInk
                            font.family: "monospace"; font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }
}
