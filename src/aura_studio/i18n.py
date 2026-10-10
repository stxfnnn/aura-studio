"""Interface languages. Source strings are German; other languages are looked up here."""
from __future__ import annotations

from PySide6.QtCore import QLocale

LANGUAGES = ("de", "en")
_active = "de"


def system_language() -> str:
    for name in QLocale.system().uiLanguages() or [QLocale.system().name()]:
        code = name.replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


def set_language(choice: str) -> None:
    """``choice`` is a language code or "system"."""
    global _active
    _active = choice if choice in LANGUAGES else system_language()


def language() -> str:
    return _active


def table() -> dict[str, str]:
    return EN if _active == "en" else {}


def decimal(value: float, digits: int = 1) -> str:
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if _active == "de" else text


def tr(text: str) -> str:
    return EN.get(text, text) if _active == "en" else text


EN: dict[str, str] = {
    # ------------------------------------------------------------ navigation
    "Übersicht": "Overview", "GERÄTE": "DEVICES", "Profile": "Profiles", "Einstellungen": "Settings",
    "OLED-Display": "OLED display", "für Linux": "for Linux", "Kein Adapter": "No adapter",
    "Bedienklänge aus": "Turn interface sounds off", "Bedienklänge an": "Turn interface sounds on",
    "Aura Studio öffnen": "Open Aura Studio", "Beenden": "Quit",
    # -------------------------------------------------------------- overview
    "Neu suchen": "Scan again", "  ·  Helligkeit ": "  ·  Brightness ", "Beleuchtung aus": "Lighting off",
    "Simulation": "Simulation", "Verbunden · ": "Connected · ", "Akku ": "Battery ",
    " Tasten einzeln": " keys, each on its own", "1 LED": "1 LED", "An": "On", "Aus": "Off",
    "Beleuchtung": "Lighting", "ERKANNT, ABER NICHT STEUERBAR": "DETECTED, BUT NOT CONTROLLABLE",
    "Tastatur": "Keyboard", "Maus": "Mouse", "Empfänger": "Receiver", "ASUS-Gerät": "ASUS device",
    "Peripherie": "Peripheral",
    # ---------------------------------------------------------------- studio
    "Geräte gekoppelt: Änderungen gelten für alle": "Devices linked: changes apply to all of them",
    "Geräte koppeln": "Link devices", "Beleuchtung ausschalten": "Turn lighting off",
    "Beleuchtung einschalten": "Turn lighting on", "AUS": "OFF", "VORSCHAU": "PREVIEW",
    "Radierer": "Eraser", "Klicken und ziehen malt · Rechtsklick löscht": "Click and drag paints · right click erases",
    "Effekte": "Effects", "Alle": "All", "Effekt zurücksetzen": "Reset effect", "FARBEN": "COLOURS",
    "Zufällige Palette": "Random palette", "Farbe ": "Colour ", "Farbe entfernen": "Remove colour",
    "Farbe hinzufügen": "Add colour", "EINSTELLUNGEN": "SETTINGS", "Helligkeit": "Brightness",
    "PROFILE": "PROFILES", "Aktuellen Stand speichern als …": "Save current look as …",
    "Als Profil speichern": "Save as profile", "ZULETZT": "RECENT",
    "Pfeile": "Arrows", "Buchstaben": "Letters", "Zahlen": "Numbers", "F-Tasten": "F keys",
    "Sondertasten": "Modifiers",
    # -------------------------------------------------------------- profiles
    "Gespeicherte Lichtstimmungen. Ein Klick wendet sie auf das ausgewählte Gerät an.":
        "Saved lighting setups. One click applies them to the selected device.",
    "Aktiv": "Active", "Profil löschen": "Delete profile", "Wirklich löschen?": "Really delete?",
    "Löschen": "Delete", "Abbrechen": "Cancel", "Noch keine Profile": "No profiles yet",
    "Stelle im Studio einen Effekt ein und speichere ihn rechts unten als Profil.":
        "Set up an effect in the studio and save it as a profile at the bottom right.",
    "Bitte gib dem Profil einen Namen.": "Please give the profile a name.",
    "Profil konnte nicht gespeichert werden: {error}": "Could not save the profile: {error}",
    "Profil „{name}“ gespeichert": "Profile “{name}” saved",
    "Profil konnte nicht geladen werden.": "Could not load the profile.",
    "Profil „{name}“ geladen": "Profile “{name}” loaded",
    "Profil konnte nicht gelöscht werden: {error}": "Could not delete the profile: {error}",
    "Profil gelöscht": "Profile deleted",
    # ------------------------------------------------------------------ oled
    "Bild oder Animation wählen": "Choose an image or animation",
    "Bilder und Animationen (*.gif *.png *.jpg *.jpeg *.bmp *.webp *.svg)":
        "Images and animations (*.gif *.png *.jpg *.jpeg *.bmp *.webp *.svg)",
    "Alle Dateien (*)": "All files (*)",
    "  ·  Der Inhalt wird in der Tastatur gespeichert und läuft dort auch ohne Aura Studio weiter.":
        "  ·  Content is stored in the keyboard and keeps playing there without Aura Studio.",
    "Display an": "Display on", "Display aus": "Display off",
    "Display ausschalten": "Turn display off", "Display einschalten": "Turn display on",
    "Animation": "Animation", "Bild / GIF": "Image / GIF", "Text": "Text",
    "MITGELIEFERTE ANIMATIONEN": "BUNDLED ANIMATIONS", "Keine Datei gewählt": "No file chosen",
    "Datei wählen …": "Choose file …", "Anpassung": "Scaling", "Einpassen": "Fit", "Füllen": "Fill",
    "Strecken": "Stretch", "Längste Animation": "Longest animation", "16 Bilder": "16 frames",
    "Schriftgröße": "Font size", "Fett": "Bold", "Lauftext": "Scrolling text", "Geschwindigkeit": "Speed",
    "Invertieren": "Invert", "Helligkeit  ·  ": "Brightness  ·  ",
    "Die Helligkeit wird in den Inhalt eingerechnet und gilt ab der nächsten Übertragung.":
        "Brightness is baked into the content and takes effect with the next transfer.",
    "Wird übertragen …": "Transferring …", "Auf Display übertragen": "Send to display",
    "Während der Übertragung pausiert die Tastenbeleuchtung. Bitte die Tastatur dabei nicht ausschalten.":
        "Key lighting pauses during the transfer. Please do not switch the keyboard off meanwhile.",
    "Live-Uhr": "Live clock",
    "Zeigt Datum und Uhrzeit mit Sekunden an. Die Tastatur zählt nicht selbst weiter, deshalb läuft die Uhr nur, solange Aura Studio geöffnet ist. Zum Zurückwechseln erneut einen Inhalt übertragen oder eine Werksanimation wählen.":
        "Shows date and time with seconds. The keyboard does not keep counting on its own, so the clock only runs while Aura Studio is open. To switch back, send content again or pick a factory animation.",
    "Werksanimationen von ASUS": "ASUS factory animations",
    "Sechs Animationen sind ab Werk fest in der Tastatur gespeichert – dieselben, die Armoury Crate als Standard anbietet. ":
        "Six animations ship stored inside the keyboard – the same ones Armoury Crate offers as defaults. ",
    "Ein Klick schaltet sofort darauf um, ohne Übertragung. Wie sie aussehen, zeigt nur das Display selbst; eine Vorschau gibt es hier nicht. ":
        "One click switches to them instantly, with no transfer. Only the display itself shows what they look like; there is no preview here. ",
    "Dein eigener Inhalt erscheint wieder, sobald du ihn erneut überträgst.":
        "Your own content comes back as soon as you send it again.",
    "Werk ": "Factory ",
    "Die Datei konnte nicht gelesen werden.": "The file could not be read.",
    "Das Display antwortet nicht. Ist die Tastatur eingeschaltet und wach?":
        "The display does not answer. Is the keyboard switched on and awake?",
    "Unvollständiger HID-Bericht an das Display.": "Incomplete HID report to the display.",
    "Die Tastatur hat den Befehl abgelehnt.": "The keyboard rejected the command.",
    "Übertragung bei {percent} % abgebrochen: keine Bestätigung von der Tastatur. Es wurde nichts gespeichert; falls das Display schwarz bleibt, die Tastatur kurz aus- und einschalten.":
        "Transfer aborted at {percent} %: no acknowledgement from the keyboard. Nothing was stored; if the display stays black, switch the keyboard off and on again.",
    "Auf das Display übertragen": "Sent to the display",
    "{count} Bilder · Schleife {loop} s · Übertragung etwa {seconds} s": "{count} frames · loop {loop} s · transfer about {seconds} s",
    "Standbild · Übertragung etwa {seconds} s": "Still image · transfer about {seconds} s",
    "Display eingeschaltet": "Display switched on", "Display ausgeschaltet": "Display switched off",
    "Noch keine Datei gewählt.": "No file chosen yet.",
    "Werksanimation {number} aktiv": "Factory animation {number} active",
    "Uhr angehalten: Display nicht erreichbar ({error})": "Clock stopped: display not reachable ({error})",
    "Display nicht erreichbar: {error}": "Display not reachable: {error}",
    "Wellen": "Waves", "Sternenflug": "Starflight", "Equalizer": "Equalizer", "Herzlinie": "Heartbeat line",
    "Scanner": "Scanner", "Umlaufbahn": "Orbit", "Flammen": "Flames", "Radar": "Radar", "Tunnel": "Tunnel",
    "Bälle": "Balls", "Schnee": "Snow", "Ringe": "Rings", "Schleife": "Loop", "Doppelhelix": "Double helix",
    "Augen": "Eyes", "Tippen": "Typing",
    # -------------------------------------------------------------- settings
    "DARSTELLUNG": "APPEARANCE", "Sprache": "Language",
    "„System“ richtet sich nach der Sprache deines Desktops.": "“System” follows the language of your desktop.",
    "Erscheinungsbild": "Theme", "„System“ folgt der Einstellung deines Desktops.": "“System” follows your desktop setting.",
    "Dunkel": "Dark", "Hell": "Light", "System": "System", "Akzentfarbe": "Accent colour",
    "Färbt Schaltflächen, Regler und Markierungen.": "Tints buttons, sliders and highlights.",
    "Folgt dem Effekt": "Follows the effect", "Eigene Farbe": "Custom colour",
    "KLANG": "SOUND", "Bedienklänge": "Interface sounds",
    "Leise Töne beim Klicken, Umschalten und Speichern.": "Quiet tones when clicking, toggling and saving.",
    "Lautstärke": "Volume", "Testen": "Test", "BELEUCHTUNG": "LIGHTING",
    "Effekt und Farben gelten für alle Geräte gleichzeitig.": "Effect and colours apply to all devices at once.",
    "Bei OLED-Übertragung alle Geräte pausieren": "Pause all devices during OLED transfers",
    "Hält auch die Beleuchtung der Maus an, solange Inhalte ans Display gesendet werden. Kann die Übertragung etwas beschleunigen, weil der Empfänger dann nur für das Display funkt.":
        "Also holds the mouse lighting while content is sent to the display. This can speed the transfer up a little, because the receiver then only talks to the display.",
    "Bildrate": "Frame rate",
    "Mehr Bilder pro Sekunde wirken flüssiger, belasten aber die Funkverbindung stärker.":
        "More frames per second look smoother but put more load on the wireless link.",
    "Sparsam": "Economical", "Ausgewogen": "Balanced", "Flüssig": "Smooth",
    "Tastaturlayout": "Keyboard layout",
    "Bestimmt Beschriftung und Tastenform in der Vorschau.": "Sets legends and key shapes in the preview.",
    "Deutsch (ISO)": "German (ISO)", "US (ANSI)": "US (ANSI)", "VERHALTEN": "BEHAVIOUR",
    "Im Hintergrund weiterlaufen": "Keep running in the background",
    "Beim Schließen des Fensters bleibt Aura Studio im Systemabschnitt der Kontrollleiste aktiv, damit die Effekte weiterlaufen.":
        "When the window is closed, Aura Studio stays in the system tray so the effects keep running.",
    "Beim Beenden an die Firmware übergeben": "Hand over to the firmware on quit",
    "Die Tastatur wechselt auf den ähnlichsten eingebauten Effekt, statt beim letzten Bild stehen zu bleiben.":
        "The keyboard switches to the closest built-in effect instead of freezing on the last frame.",
    "ERKANNTE HARDWARE": "DETECTED HARDWARE", "Steuerbar": "Controllable",
    "DIAGNOSEPROTOKOLL": "DIAGNOSTIC LOG", "Laden": "Load", "Kopieren": "Copy",
    "  ·  Seriennummern werden nicht protokolliert.": "  ·  Serial numbers are not logged.",
    "Protokoll konnte nicht gelesen werden: {error}": "Could not read the log: {error}",
    "Diagnoseprotokoll in die Zwischenablage kopiert": "Diagnostic log copied to the clipboard",
    # --------------------------------------------------------------- devices
    "Vorschau-Tastatur": "Preview keyboard", "Vorschau-Maus": "Preview mouse",
    "Kein Gerät verbunden · Effekte laufen nur in der Vorschau": "No device connected · effects run in the preview only",
    "Mausrad-LED · nur Vorschau": "Scroll wheel LED · preview only", "ASUS HID-Gerät": "ASUS HID device",
    "2,4 GHz direkt": "2.4 GHz direct",
    "Einzeltasten-RGB · Aura-TUF direkt · {link}": "Per-key RGB · Aura TUF direct · {link}",
    "Erkannt · noch kein nativer Adapter": "Detected · no native adapter yet",
    "Einzeltasten-RGB · Aura-TUF über Omni Receiver · Report-ID {channel}": "Per-key RGB · Aura TUF via Omni Receiver · report ID {channel}",
    "ROG Maus ({pid})": "ROG mouse ({pid})",
    "Dongle-Schnittstelle {interface} · gekoppelte Geräte werden als HID-Kanäle geführt":
        "Dongle interface {interface} · paired devices appear as HID channels",
    "Mausrad-LED · HID LampArray": "Scroll wheel LED · HID LampArray",
    "Gekoppeltes Gerät · Report-ID {channel} · keine LampArray-Schnittstelle": "Paired device · report ID {channel} · no LampArray interface",
    "Keine Berechtigung für {path}. Installiere die udev-Regel aus packaging/99-aura-studio.rules.":
        "No permission for {path}. Install the udev rule from packaging/99-aura-studio.rules.",
    "{name}: Verbindung unterbrochen ({error}).": "{name}: connection lost ({error}).",
    "{name}: Effekt wurde unerwartet beendet.": "{name}: the effect stopped unexpectedly.",
    "Die Mausrad-LED meldet kein programmierbares RGB-LampArray.": "The scroll wheel LED does not report a programmable RGB LampArray.",
    "Unvollständiger HID-Bericht ({written}/{total} Bytes)": "Incomplete HID report ({written}/{total} bytes)",
    "Kein steuerbares Gerät – Vorschau-Modus": "No controllable device – preview mode",
    "{name} verbunden": "{name} connected", "{count} Geräte verbunden": "{count} devices connected",
    # --------------------------------------------------------------- effects
    "Basis": "Basics", "Fluss": "Flow", "Natur": "Nature", "Partikel": "Particles",
    "Einfarbig": "Solid", "Eine ruhige, gleichmäßige Farbe auf allen Tasten.": "One calm, even colour on every key.",
    "Farbe": "Colour", "Farbe 1": "Colour 1", "Farbe 2": "Colour 2", "Farbe 3": "Colour 3", "Farbe 4": "Colour 4",
    "Verlauf": "Gradient",
    "Weicher Farbverlauf über das ganze Gerät – still oder langsam wandernd.": "A soft gradient across the whole device – still or slowly drifting.",
    "Drift": "Drift", "Richtung": "Direction", "Streckung": "Stretch",
    "Atmen": "Breathing",
    "Sanftes Ein- und Ausblenden. Mehrere Farben wechseln sich pro Atemzug ab.": "Gentle fading in and out. Several colours take turns, one per breath.",
    "Tiefe": "Depth", "Eigene Tasten": "Custom keys",
    "Male jede Taste einzeln an – direkt in der Vorschau, mit Klicken und Ziehen.": "Paint every key on its own – right in the preview, by clicking and dragging.",
    "Grundfarbe": "Base colour", "Regenbogenwelle": "Rainbow wave",
    "Das volle Spektrum zieht als Welle über die Tasten.": "The full spectrum sweeps across the keys as a wave.",
    "Wellenlänge": "Wavelength", "Sättigung": "Saturation", "Farbzyklus": "Colour cycle",
    "Alle Tasten wandern gemeinsam durch das Farbspektrum.": "All keys travel through the colour spectrum together.",
    "Farbwelle": "Colour wave",
    "Deine eigenen Farben rollen als weiche Welle in eine Richtung.": "Your own colours roll in one direction as a soft wave.",
    "Wirbel": "Swirl", "Farben drehen sich wie ein Strudel um die Mitte der Tastatur.": "Colours spin around the centre of the keyboard like a whirlpool.",
    "Verdrehung": "Twist", "Armbreite": "Arm width", "Plasma": "Plasma",
    "Organisch ineinanderfließende Farbfelder, wie flüssiges Licht.": "Fields of colour flowing into each other, like liquid light.",
    "Kontrast": "Contrast", "Mustergröße": "Pattern size", "Pulsringe": "Pulse rings",
    "Farbringe breiten sich von der Mitte nach außen aus.": "Rings of colour spread outwards from the centre.",
    "Ringabstand": "Ring spacing", "Feuer": "Fire",
    "Flammen brennen von der untersten Reihe nach oben. Die Spitzen leuchten heller, flackern und werfen Funken.":
        "Flames burn upwards from the bottom row. The tips glow brighter, flicker and throw sparks.",
    "Glut": "Embers", "Flamme": "Flame", "Spitze": "Tip", "Flammenhöhe": "Flame height", "Flammenbreite": "Flame width",
    "Ozean": "Ocean", "Dünung rollt über die Tasten, Schaumkronen blitzen auf den Wellenkämmen.": "Swell rolls across the keys, foam flashes on the crests.",
    "Wasser": "Water", "Schaum": "Foam", "Schaumkronen": "Whitecaps", "Wellengröße": "Wave size",
    "Polarlicht": "Aurora", "Schimmernde Lichtvorhänge wandern langsam über einen dunklen Himmel.": "Shimmering curtains of light drift slowly across a dark sky.",
    "Vorhanghöhe": "Curtain height", "Breite": "Width", "Lava": "Lava",
    "Zähe, glühende Ströme schieben sich unter einer dunklen Kruste hindurch.": "Thick, glowing streams push along beneath a dark crust.",
    "Kruste": "Crust", "Härte": "Hardness", "Stromgröße": "Stream size", "Gewitter": "Thunderstorm",
    "Dunkle Wolken, fallender Regen – und Blitze, die quer über die Tastatur zucken.": "Dark clouds, falling rain – and lightning that cracks across the keyboard.",
    "Wolken": "Clouds", "Regen": "Rain", "Blitz": "Lightning", "Blitzhäufigkeit": "Lightning rate", "Wolkengröße": "Cloud size",
    "Matrix-Regen": "Matrix rain",
    "Leuchtende Tropfen fallen spaltenweise herab und ziehen einen Schweif hinter sich her.": "Glowing drops fall column by column, trailing a tail behind them.",
    "Schweif": "Tail", "Kopf": "Head", "Dichte": "Density", "Schweiflänge": "Tail length",
    "Sternenhimmel": "Starry sky", "Einzelne Tasten funkeln zufällig auf und verglühen wieder.": "Single keys twinkle at random and fade away again.",
    "Himmel": "Sky", "Stern 1": "Star 1", "Stern 2": "Star 2", "Stern 3": "Star 3", "Sternendichte": "Star density",
    "Regentropfen": "Raindrops", "Tropfen fallen auf die Tastatur und schicken Ringe über die Nachbartasten.": "Drops land on the keyboard and send rings across the neighbouring keys.",
    "Grund": "Ground", "Tropfen 1": "Drop 1", "Tropfen 2": "Drop 2", "Tropfenmenge": "Drop rate", "Ringbreite": "Ring width",
    "Komet": "Comet", "Lichtpunkte schießen mit langem Schweif über die Tasten.": "Points of light shoot across the keys with a long tail.",
    "Hintergrund": "Background", "Anzahl": "Count", "Herzschlag": "Heartbeat",
    "Ein doppelter Pulsschlag, der sich von der Mitte nach außen ausbreitet.": "A double beat that spreads outwards from the centre.",
    "Puls": "Pulse", "Ausbreitung": "Spread",
}
