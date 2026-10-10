pragma Singleton
import QtQuick

// Interface language. Source strings are German; ``table`` maps them to the
// active language (empty for German) and is set from Main.qml.
QtObject {
    property var table: ({})
    function t(text) {
        var translated = table[text]
        return translated !== undefined ? translated : text
    }
}
