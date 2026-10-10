# Aura Studio

Eine moderne Linux-Oberfläche für ASUS- und ROG-Peripherie. Qt 6 / QML passt sich an KDE Plasma und Wayland an. Die Gerätekommunikation erfolgt über einen eigenen Linux-`hidraw`-Adapter; OpenRGB ist keine Laufzeitabhängigkeit.

## Aktueller Umfang

- Direkte HID-Suche nach ASUS-Geräten über Linux sysfs.
- Eigener Aura-TUF-Protokolladapter für ROG Azoth per USB, direktem 2,4-GHz-Modus und über den erkannten Omni-Tastaturkanal.
- ROG Harpe Ace Extreme: einzelne Mausrad-LED über HID LampArray; Farbe und Helligkeit per Standard-Feature-Reports.
- Neun Effekte: statische Farbe, Atmen, Regenbogen, Farbzyklus, Puls, Ozean, Aurora, Feuer und Pastellfluss. Farbzyklus und zusätzliche Animationen werden als sparsame HID-Updates im Hintergrund erzeugt.
- Eigene HSV-Farbfläche mit HEX-Eingabe, Preset-Farben, Helligkeits- und Geschwindigkeitseinstellung.
- Profile werden lokal als JSON gespeichert und können geladen, überschrieben oder gelöscht werden.
- Detaillierte HID-Erkennung mit Schnittstellen, Report-IDs, Gerätepfaden und gesendeten Berichten im Diagnoseprotokoll; Seriennummern werden ausgelassen.
- Qt/QML-Oberfläche mit Geräte-Seiten, Hover- und Auswahlrückmeldung, Statusmeldungen, leisen Bedienklängen mit Ein/Aus-Schalter und Diagnoseansicht.
- Editierbare Geräte werden getrennt von erkannter, derzeit nicht editierbarer Hardware angezeigt. Letztere ist unter „Erkannt, nicht editierbar“ einklappbar.
- Azoth-OLED: noch kein eingebauter, validierter Schreibadapter für das klassische ROG Azoth.

## Start auf Fedora KDE

```bash
sudo dnf install python3-pyside6
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
aura-studio
```

Für HID-Zugriff können passende udev-Rechte nötig sein. Eine eng auf die unterstützten Azoth-USB-IDs begrenzte Regel liegt unter `packaging/99-aura-studio.rules`. Installiere sie bei Bedarf nach `/etc/udev/rules.d/` und lade die udev-Regeln neu.

## Installation als Benutzer-App

```bash
./packaging/install-user.sh
```

Das Skript legt einen Starter unter `~/.local/share/applications` an. Es installiert keine privilegierten udev-Regeln.

## Architektur

- `src/aura_studio/main.py`: Qt-App-Einstiegspunkt.
- `src/aura_studio/backend.py`: HID-Erkennung, native HID-Kommunikation, Profile und rotierende Diagnoseprotokolle.
- `src/aura_studio/qml/Main.qml`: Oberfläche.
- `src/aura_studio/adapters/`: Treiberintegrationen nach Gerätefamilie.

### Unterstützungsmodell

Es gibt keine einzelne universelle ASUS-Schnittstelle für alle Mäuse, Tastaturen, OLEDs und Mainboards. Das native Backend steuert das klassische ROG Azoth über den Aura-TUF-HID-Kanal und die einzelne RGB-Lampe der Harpe Ace Extreme über den standardisierten HID LampArray-Kanal. Software-Animationen laufen, solange Aura Studio geöffnet ist; beim Beenden wird die autonome Mausrad-Beleuchtung wieder aktiviert. Der Azoth-OLED-Adapter fehlt weiterhin.

Das rotierende Protokoll liegt unter `${XDG_STATE_HOME:-~/.local/state}/aura-studio/aura-studio.log`. Die Diagnoseansicht zeigt HID-Knoten, Report-IDs, Scan-Ergebnisse und Schreibversuche; das Protokoll kann aus der App kopiert werden.

## Lizenz

MIT. Nicht mit ASUS verbunden. ASUS und ROG sind Marken ihrer jeweiligen Inhaber.
