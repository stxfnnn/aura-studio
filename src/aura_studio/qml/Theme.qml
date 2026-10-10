pragma Singleton
import QtQuick

QtObject {
    // Set from Main.qml: light or dark surfaces, and the accent colour.
    property bool dark: true
    property color accent: defaultAccent
    readonly property color defaultAccent: "#9b7dff"

    // Surfaces, from the window background up to hovered controls.
    readonly property color bg: dark ? "#09090c" : "#f3f3f7"
    readonly property color panel: dark ? "#101014" : "#e9e9ef"
    readonly property color card: dark ? "#15151b" : "#ffffff"
    readonly property color raised: dark ? "#1c1c24" : "#f1f1f5"
    readonly property color hover: dark ? "#24242e" : "#e2e2ea"
    readonly property color popup: dark ? "#1b1b23" : "#ffffff"
    readonly property color stroke: dark ? "#22ffffff" : "#26000000"
    readonly property color strokeSoft: dark ? "#12ffffff" : "#14000000"
    // Device previews stay dark in both themes: they show light, not paper.
    readonly property color well: "#0b0b0e"

    readonly property color text: dark ? "#f3f3f8" : "#15151a"
    readonly property color textDim: dark ? "#a3a3b2" : "#50505c"
    readonly property color textFaint: dark ? "#6a6a79" : "#84848f"
    readonly property color good: dark ? "#5fe0a4" : "#17995d"
    readonly property color bad: dark ? "#ff6b81" : "#d92f4b"

    readonly property color accentInk: dark ? "#0b0b10" : "#ffffff"
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, dark ? 0.14 : 0.12)
    readonly property color accentLine: Qt.rgba(accent.r, accent.g, accent.b, 0.55)

    readonly property int radius: 16
    readonly property int radiusSmall: 10
    readonly property int quick: 130
    readonly property int smooth: 240
}
