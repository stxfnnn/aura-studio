"""Physical key layout of the ROG Azoth (75 %).

LED ids follow the Aura TUF per-key scheme used by the firmware:
``id = matrix_column * 8 + matrix_row``. Positions are in key units
(1.0 = one regular keycap), origin at the top-left corner of Escape.
"""
from __future__ import annotations

from dataclasses import dataclass

WIDTH = 16.25
HEIGHT = 6.25


@dataclass(frozen=True)
class Key:
    id: int
    label: str
    x: float
    y: float
    w: float = 1.0
    h: float = 1.0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


_LABELS = {
    "de": {
        "num": ["^", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "ß", "´"],
        "top": ["Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "Ü", "+"],
        "home": ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ö", "Ä"],
        "bottom": ["Y", "X", "C", "V", "B", "N", "M", ",", ".", "-"],
        "iso": True,
    },
    "us": {
        "num": ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
        "top": ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]"],
        "home": ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"],
        "bottom": ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"],
        "iso": False,
    },
}

LAYOUTS = {"de": "Deutsch (ISO)", "us": "US (ANSI)"}


def azoth_keys(layout: str = "de") -> list[Key]:
    labels = _LABELS.get(layout, _LABELS["de"])
    iso = labels["iso"]
    keys: list[Key] = [Key(0x00, "Esc", 0, 0)]
    # Function row: three blocks of four, matrix columns 1..12.
    for index in range(12):
        x = 1.25 + index + 0.25 * (index // 4)
        keys.append(Key((index + 1) * 8, f"F{index + 1}", x, 0))
    # Number row: matrix columns 0..12, row 1.
    for index, label in enumerate(labels["num"]):
        keys.append(Key(index * 8 + 1, label, index, 1.25))
    keys.append(Key(0x69, "⌫", 13, 1.25, 2))
    # Top letter row: Tab is column 0, letters start at column 1.
    keys.append(Key(0x02, "Tab", 0, 2.25, 1.5))
    for index, label in enumerate(labels["top"]):
        keys.append(Key((index + 1) * 8 + 2, label, 1.5 + index, 2.25))
    # Home row.
    keys.append(Key(0x03, "Caps", 0, 3.25, 1.75))
    for index, label in enumerate(labels["home"]):
        keys.append(Key((index + 1) * 8 + 3, label, 1.75 + index, 3.25))
    if iso:
        # ISO moves "#" into matrix column 12 of the home row; the tall Enter
        # keeps the ANSI Enter LED (column 13, row 3).
        keys.append(Key(0x63, "#", 12.75, 3.25))
        keys.append(Key(0x6B, "⏎", 13.75, 2.25, 1.25, 2))
        keys.append(Key(0x04, "⇧", 0, 4.25, 1.25))
        keys.append(Key(0x0C, "<", 1.25, 4.25))
    else:
        keys.append(Key(0x6A, "\\", 13.5, 2.25, 1.5))
        keys.append(Key(0x6B, "⏎", 12.75, 3.25, 2.25))
        keys.append(Key(0x04, "⇧", 0, 4.25, 2.25))
    # Bottom letter row: matrix columns 2..11, row 4.
    for index, label in enumerate(labels["bottom"]):
        keys.append(Key((index + 2) * 8 + 4, label, 2.25 + index, 4.25))
    keys.append(Key(0x64, "⇧", 12.25, 4.25, 1.75))
    # Modifier row.
    keys.append(Key(0x05, "Strg" if iso else "Ctrl", 0, 5.25, 1.25))
    keys.append(Key(0x0D, "❖", 1.25, 5.25, 1.25))
    keys.append(Key(0x15, "Alt", 2.5, 5.25, 1.25))
    keys.append(Key(0x35, "", 3.75, 5.25, 6.25))
    keys.append(Key(0x55, "AltGr" if iso else "Alt", 10, 5.25))
    keys.append(Key(0x5D, "Fn", 11, 5.25))
    keys.append(Key(0x65, "Strg" if iso else "Ctrl", 12, 5.25))
    # Navigation column and arrows.
    keys.append(Key(0x79, "Einf" if iso else "Ins", 15.25, 1.25))
    keys.append(Key(0x7A, "Entf" if iso else "Del", 15.25, 2.25))
    keys.append(Key(0x7B, "Bild↑" if iso else "PgUp", 15.25, 3.25))
    keys.append(Key(0x7C, "Bild↓" if iso else "PgDn", 15.25, 4.25))
    keys.append(Key(0x74, "↑", 14.25, 4.25))
    keys.append(Key(0x6D, "←", 13.25, 5.25))
    keys.append(Key(0x75, "↓", 14.25, 5.25))
    keys.append(Key(0x7D, "→", 15.25, 5.25))
    return keys
