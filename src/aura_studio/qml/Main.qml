import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: app
    width: 1360
    height: 860
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    title: "Aura Studio"
    color: Theme.bg

    property string page: "home"
    property var frame: []
    readonly property var catalog: service.catalog
    readonly property var devices: service.devices
    readonly property var cfg: service.config
    readonly property string effectId: cfg.effect || ""
    readonly property var effectDef: catalog.find(effect => effect.id === effectId) || null
    readonly property var device: devices.find(candidate => candidate.id === service.selected) || null

    readonly property var settings: service.settings
    readonly property bool dark: settings.theme === "dark"
                                 || (settings.theme === "system" && Qt.styleHints.colorScheme !== Qt.Light)

    // The accent is either the user's own colour or the most vivid colour of the running effect.
    readonly property color accentTarget: {
        var best = null
        if (settings.accentMode === "custom") {
            best = Qt.color(settings.accentColor)
        } else {
            var score = 0.3
            var colors = cfg.colors || []
            for (var i = 0; i < colors.length; i++) {
                var c = Qt.color(colors[i])
                if (c.hsvSaturation * c.hsvValue > score) { score = c.hsvSaturation * c.hsvValue; best = c }
            }
            if (!best) best = Theme.defaultAccent
        }
        // Keep it readable: bright on dark surfaces, deeper on light ones.
        var hue = Math.max(0, best.hsvHue), saturation = best.hsvSaturation
        if (settings.accentMode !== "custom") saturation = Math.max(0.4, Math.min(dark ? 0.72 : 0.9, saturation))
        return dark ? Qt.hsva(hue, saturation, Math.max(0.75, best.hsvValue), 1)
                    : Qt.hsva(hue, Math.max(saturation, saturation > 0.05 ? 0.5 : 0), Math.min(0.72, Math.max(0.35, best.hsvValue)), 1)
    }
    property color accent: accentTarget
    Behavior on accent { ColorAnimation { duration: 500; easing.type: Easing.OutCubic } }
    Binding { target: Theme; property: "accent"; value: app.accent }
    Binding { target: Theme; property: "dark"; value: app.dark }
    Binding { target: L; property: "table"; value: service.translations }
    Binding { target: Sfx; property: "enabled"; value: service.settings.sounds }
    Binding { target: Sfx; property: "volume"; value: service.settings.volume / 100 }

    function go(target) {
        if (page === target) return
        Sfx.play("nav")
        page = target
    }

    onClosing: close => {
        if (service.settings.tray && trayAvailable) {
            close.accepted = false
            app.hide()
        }
    }

    Connections {
        target: service
        function onFrameReady(colors) { app.frame = colors }
        function onNotify(text, kind) {
            toast.show(text, kind)
            if (kind === "success" || kind === "error") Sfx.play(kind)
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ----------------------------------------------------------- sidebar
        Rectangle {
            Layout.preferredWidth: 236
            Layout.fillHeight: true
            color: Theme.panel
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.strokeSoft }

            component SectionLabel: Text {
                color: Theme.textFaint
                font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
                leftPadding: 10
            }
            component NavRow: Rectangle {
                id: nav
                property string icon: ""
                property string label: ""
                property string sub: ""
                property bool current: false
                property bool dim: false
                property bool dot: false
                signal clicked()
                Layout.fillWidth: true
                implicitHeight: sub !== "" ? 52 : 42
                radius: 12
                color: current ? Theme.accentSoft : navArea.containsMouse && !dim ? Theme.raised : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.quick } }
                Rectangle {
                    width: 3; height: nav.current ? 18 : 0; radius: 1.5
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.accent
                    Behavior on height { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutBack } }
                }
                Icon {
                    x: 14
                    anchors.verticalCenter: parent.verticalCenter
                    name: nav.icon
                    color: nav.current ? Theme.accent : nav.dim ? Theme.textFaint : Theme.textDim
                }
                Column {
                    x: 44
                    width: parent.width - 44 - (nav.dot ? 26 : 10)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Text {
                        width: parent.width
                        text: nav.label
                        color: nav.current ? Theme.text : nav.dim ? Theme.textFaint : Theme.textDim
                        font.pixelSize: 13; font.weight: nav.current ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                    }
                    Text {
                        visible: nav.sub !== ""
                        width: parent.width
                        text: nav.sub
                        color: Theme.textFaint
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }
                Rectangle {
                    visible: nav.dot
                    width: 8; height: 8; radius: 4
                    anchors.right: parent.right; anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.good
                }
                MouseArea {
                    id: navArea
                    anchors.fill: parent
                    enabled: !nav.dim
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: nav.clicked()
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                anchors.topMargin: 22
                spacing: 4

                RowLayout {
                    Layout.leftMargin: 8
                    Layout.bottomMargin: 22
                    spacing: 11
                    Rectangle {
                        implicitWidth: 34; implicitHeight: 34; radius: 11
                        gradient: Gradient {
                            GradientStop { position: 0; color: Qt.lighter(Theme.accent, 1.15) }
                            GradientStop { position: 1; color: Qt.darker(Theme.accent, 1.7) }
                        }
                        Icon { anchors.centerIn: parent; name: "spark"; size: 17; color: "#ffffff"; weight: 2 }
                        border.width: Theme.dark ? 0 : 1
                        border.color: "#20000000"
                    }
                    Column {
                        spacing: 0
                        Text { text: "Aura Studio"; color: Theme.text; font.pixelSize: 15; font.weight: Font.Bold }
                        Text { text: L.t("für Linux"); color: Theme.textFaint; font.pixelSize: 11 }
                    }
                }

                NavRow { icon: "home"; label: L.t("Übersicht"); current: app.page === "home"; onClicked: app.go("home"); Layout.bottomMargin: 14 }
                SectionLabel { text: L.t("GERÄTE"); Layout.bottomMargin: 4 }
                Repeater {
                    model: app.devices
                    delegate: NavRow {
                        icon: modelData.category === "Tastatur" ? "keyboard" : modelData.category === "Maus" ? "mouse" : "chip"
                        label: modelData.name
                        sub: modelData.controllable ? modelData.source : L.t("Kein Adapter")
                        dim: !modelData.controllable
                        dot: modelData.controllable && !modelData.virtual
                        current: app.page === "studio" && modelData.id === service.selected
                        onClicked: {
                            if (current) return
                            Sfx.play("nav")
                            service.selectDevice(modelData.id)
                            app.page = "studio"
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                NavRow { visible: oled.available; icon: "display"; label: L.t("OLED-Display"); current: app.page === "oled"; onClicked: app.go("oled") }
                NavRow { icon: "layers"; label: L.t("Profile"); current: app.page === "profiles"; onClicked: app.go("profiles") }
                NavRow { icon: "sliders"; label: L.t("Einstellungen"); current: app.page === "settings"; onClicked: app.go("settings") }

                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.strokeSoft; Layout.topMargin: 8; Layout.bottomMargin: 8 }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 10
                    spacing: 8
                    Text {
                        Layout.fillWidth: true
                        text: service.status
                        color: Theme.textFaint
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                    IconButton {
                        icon: service.settings.sounds ? "volume" : "mute"
                        tip: service.settings.sounds ? L.t("Bedienklänge aus") : L.t("Bedienklänge an")
                        flat: true; size: 30
                        sound: ""
                        onClicked: { service.setSetting("sounds", !service.settings.sounds); Sfx.play("toggle_on") }
                    }
                }
            }
        }

        // ------------------------------------------------------------- pages
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            component Page: Item {
                property bool current: false
                anchors.fill: parent
                opacity: current ? 1 : 0
                visible: opacity > 0
                enabled: current
                transform: Translate { y: current ? 0 : 14; Behavior on y { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } } }
                Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
            }

            Page {
                current: app.page === "home"
                HomePage {
                    anchors.fill: parent
                    onOpenDevice: id => { service.selectDevice(id); app.page = "studio" }
                    onOpenOled: app.page = "oled"
                }
            }
            Page {
                current: app.page === "studio"
                StudioPage {
                    anchors.fill: parent
                    cfg: app.cfg
                    device: app.device
                    effectDef: app.effectDef
                    frame: app.frame
                    picker: picker
                    catalog: app.catalog
                }
            }
            Page {
                current: app.page === "oled"
                OledPage { anchors.fill: parent }
            }
            Page {
                current: app.page === "profiles"
                ProfilesPage { anchors.fill: parent; onApplied: app.page = "studio" }
            }
            Page {
                current: app.page === "settings"
                SettingsPage { anchors.fill: parent; picker: picker }
            }
        }
    }

    ColorPicker { id: picker; parent: Overlay.overlay }
    Toast { id: toast }
}
