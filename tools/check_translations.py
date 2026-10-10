"""Check that every interface string has an English translation.

Run:  QT_QPA_PLATFORM=offscreen python tools/check_translations.py   (exit code 1 if any are missing)
"""
import re, pathlib, sys, ast
root = pathlib.Path(__file__).resolve().parent.parent / "src" / "aura_studio"
keys = {}
for f in sorted((root / "qml").glob("*.qml")):
    for m in re.finditer(r'L\.t\("((?:[^"\\]|\\.)*)"\)', f.read_text()):
        keys.setdefault(m.group(1).encode().decode("unicode_escape").encode("latin-1").decode() if "\\" in m.group(1) else m.group(1), f.name)
for f in sorted(root.glob("*.py")):
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "tr" and node.args and isinstance(node.args[0], ast.Constant):
            keys.setdefault(node.args[0].value, f.name)
sys.path.insert(0, str(root.parent))  # src/
from aura_studio import effects, oled
for e in effects._CATALOG:
    keys.setdefault(e["name"], "catalog"); keys.setdefault(e["description"], "catalog")
    for label, _ in e["colors"]: keys.setdefault(label, "catalog")
    for p in e["params"]: keys.setdefault(p["label"], "catalog")
for g in effects.GROUPS: keys.setdefault(g["name"], "catalog")
for a in oled.ANIMATIONS.values(): keys.setdefault(a[0], "oled")
for c in ("Tastatur", "Maus", "Empfänger", "Beleuchtung", "ASUS-Gerät", "Peripherie"): keys.setdefault(c, "category")
from aura_studio import i18n, macros
optional = set(macros._NAMES.values())  # key names; most are the same in every language
missing = [k for k in keys if k not in i18n.EN]
if "--all" in sys.argv:
    for k, w in keys.items(): print(repr(k))
print(len(keys), "keys,", len(missing), "missing", file=sys.stderr)
for k in missing[:400]: print("MISSING", repr(k), keys[k])
stale = [k for k in i18n.EN if k not in keys and k not in optional]
for k in stale: print("STALE", repr(k))
sys.exit(1 if missing or stale else 0)
