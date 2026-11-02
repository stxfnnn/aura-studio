"""Self-check of the fan logic on the simulated chip: ramps, panic and the hand-back to the BIOS.

Run:  QT_QPA_PLATFORM=offscreen python tools/check_fans.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from PySide6.QtCore import QCoreApplication
app = QCoreApplication([])
from aura_studio.fans import FanController

c = FanController({}, demo=True)
c._demo_tick = lambda now: None          # the test sets the temperature itself
fan = c._fans[0]
temp = c._demo / "hwmon1" / "temp1_input"
def tick(celsius):
    temp.write_text(str(celsius * 1000)); c._tick(); return fan.level
assert fan.enable.read_text() == "5" and not fan.manual
c.setFanOption(fan.id, "mode", "curve"); c.setFanOption(fan.id, "source", "cpu")
c.setFanOption(fan.id, "points", [[75, 100], [40, 30], [40, 35], ["x", 1], [120, 50]])
assert c._settings[fan.id]["points"] == [[40, 35], [75, 100], [100, 50]], "points sorted, clamped, deduplicated"
assert c._curve([[40, 30], [75, 100]], 30) == 30 and c._curve([[40, 30], [75, 100]], 90) == 100
assert c._curve([[40, 30], [60, 50], [75, 100]], 50) == 40 and c._curve([[40, 30], [60, 50], [75, 100]], 70) == 50 + 50 * 10 / 15
c.setFanOption(fan.id, "points", [[40, 30], [75, 100]])
assert FanController._clean(FanController._clean.__globals__["DEFAULT_FAN"], {"tempLow": 45, "low": 20, "tempHigh": 80, "high": 90})["points"] == [[45, 20], [80, 90]]
c.setRamp("window", 0); c.setRamp("up", 5); c.setRamp("down", 2)
start = fan.level
assert abs(tick(30) - (start - 2)) < 1e-6, "slows down by at most 2 %/s"
assert fan.enable.read_text() == "1" and fan.pwm.read_text() == str(round(fan.level * 255 / 100))
level = fan.level
assert abs(tick(80) - (level + 5)) < 1e-6, "speeds up by at most 5 %/s"
assert tick(95) == 100, "panic: full speed at once"
c.setRamp("window", 60)
assert tick(30) == 98, "smoothed temperature keeps the fan up, ramp-down limit still applies"
c.setFanOption(fan.id, "mode", "fixed"); c.setFanOption(fan.id, "fixed", 40)
for _ in range(40): tick(30)
assert fan.level == 40
c.setFanOption(fan.id, "mode", "bios"); tick(30)
assert fan.enable.read_text() == "5" and not fan.manual, "handed back to the BIOS"
c.stop()
assert not c._demo.exists()
print("fans ok")
