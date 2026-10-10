"""Per-lamp lighting effects.

Every effect renders one colour per lamp from the lamp's physical position, so
the same code drives an 80-key keyboard, a single mouse LED and the on-screen
preview. Positions are in key units (see ``layout.py``); colours are float RGB
triples in 0..1.
"""
from __future__ import annotations

import colorsys
import math
import random
import re
from dataclasses import dataclass, field as dataclass_field
from typing import Any

from . import layout
from .i18n import tr

RGB = tuple[float, float, float]
BLACK: RGB = (0.0, 0.0, 0.0)


# ---------------------------------------------------------------- colour math

def hex_to_rgb(value: str) -> RGB:
    digits = re.sub(r"[^0-9a-fA-F]", "", str(value))[:6].ljust(6, "0")
    return (int(digits[0:2], 16) / 255, int(digits[2:4], 16) / 255, int(digits[4:6], 16) / 255)


def rgb_to_bytes(color: RGB) -> tuple[int, int, int]:
    return (max(0, min(255, round(color[0] * 255))),
            max(0, min(255, round(color[1] * 255))),
            max(0, min(255, round(color[2] * 255))))


def rgb_to_hex(color: RGB) -> str:
    return "#%02x%02x%02x" % rgb_to_bytes(color)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return low if value < low else high if value > high else value


def mix(a: RGB, b: RGB, amount: float) -> RGB:
    amount = clamp(amount)
    return (a[0] + (b[0] - a[0]) * amount, a[1] + (b[1] - a[1]) * amount, a[2] + (b[2] - a[2]) * amount)


def scale(color: RGB, factor: float) -> RGB:
    return (color[0] * factor, color[1] * factor, color[2] * factor)


def add(a: RGB, b: RGB) -> RGB:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def lighten(a: RGB, b: RGB) -> RGB:
    return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 0.0 if value < edge0 else 1.0
    amount = clamp((value - edge0) / (edge1 - edge0))
    return amount * amount * (3 - 2 * amount)


def palette(colors: list[RGB], position: float) -> RGB:
    """Sample a gradient through ``colors``; position is clamped to 0..1."""
    if len(colors) == 1:
        return colors[0]
    scaled = clamp(position) * (len(colors) - 1)
    index = min(int(scaled), len(colors) - 2)
    return mix(colors[index], colors[index + 1], scaled - index)


def palette_loop(colors: list[RGB], position: float) -> RGB:
    """Sample a seamless cyclic gradient through ``colors``."""
    count = len(colors)
    if count == 1:
        return colors[0]
    scaled = (position % 1.0) * count
    index = int(scaled) % count
    amount = scaled - int(scaled)
    amount = amount * amount * (3 - 2 * amount)
    return mix(colors[index], colors[(index + 1) % count], amount)


def hsv(hue: float, saturation: float, value: float) -> RGB:
    return colorsys.hsv_to_rgb(hue % 1.0, clamp(saturation), clamp(value))


# ---------------------------------------------------------------------- noise

def _hash(ix: int, iy: int, iz: int = 0) -> float:
    n = (ix * 374761393 + iy * 668265263 + iz * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def noise2(x: float, y: float) -> float:
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    top = _hash(ix, iy) + (_hash(ix + 1, iy) - _hash(ix, iy)) * fx
    bottom = _hash(ix, iy + 1) + (_hash(ix + 1, iy + 1) - _hash(ix, iy + 1)) * fx
    return top + (bottom - top) * fy


def noise3(x: float, y: float, z: float) -> float:
    iz = math.floor(z)
    fz = z - iz
    fz = fz * fz * (3 - 2 * fz)
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)

    def plane(layer: int) -> float:
        a, b = _hash(ix, iy, layer), _hash(ix + 1, iy, layer)
        c, d = _hash(ix, iy + 1, layer), _hash(ix + 1, iy + 1, layer)
        top, bottom = a + (b - a) * fx, c + (d - c) * fx
        return top + (bottom - top) * fy

    near = plane(iz)
    return near + (plane(iz + 1) - near) * fz


def fbm2(x: float, y: float) -> float:
    return noise2(x, y) * 0.62 + noise2(x * 2.1 + 17.3, y * 2.1 + 5.1) * 0.38


# ---------------------------------------------------------------------- field

@dataclass(frozen=True)
class Lamp:
    id: int
    x: float
    y: float


@dataclass
class Field:
    lamps: list[Lamp]
    width: float = layout.WIDTH
    height: float = layout.HEIGHT

    @staticmethod
    def keyboard(keys: list[layout.Key]) -> "Field":
        lamps = [Lamp(key.id, key.cx, key.cy) for key in keys]
        # The ANSI backslash LED (0x6A) sits under the upper half of the ISO Enter.
        # Appended after the keys so preview indices still match ``keys``.
        used = {key.id for key in keys}
        lamps += [Lamp(0x6A, key.cx, key.cy) for key in keys if key.id == 0x6B and key.h > 1 and 0x6A not in used]
        return Field(lamps)

    @staticmethod
    def single() -> "Field":
        return Field([Lamp(0, layout.WIDTH / 2, layout.HEIGHT / 2)])

    @staticmethod
    def grid(columns: int, rows: int) -> "Field":
        return Field([Lamp(row * columns + column,
                           (column + 0.5) * layout.WIDTH / columns,
                           (row + 0.5) * layout.HEIGHT / rows)
                      for row in range(rows) for column in range(columns)])


@dataclass
class Params:
    colors: list[RGB]
    intensity: float = 0.5
    scale: float = 0.5
    angle: float = 0.0
    keys: dict[int, RGB] = dataclass_field(default_factory=dict)

    @property
    def zoom(self) -> float:
        """Pattern size multiplier, 0.5 (fine) .. 2 (large)."""
        return 2 ** ((self.scale - 0.5) * 2)

    def color(self, index: int) -> RGB:
        return self.colors[min(index, len(self.colors) - 1)]


class Effect:
    def __init__(self, field: Field, seed: int | None = None) -> None:
        self.field = field
        self.rng = random.Random(seed)

    def along(self, lamp: Lamp, p: Params) -> float:
        """Signed distance of the lamp from the centre along the effect direction."""
        return ((lamp.x - self.field.width / 2) * math.cos(p.angle)
                + (lamp.y - self.field.height / 2) * math.sin(p.angle))

    def radius(self, lamp: Lamp) -> float:
        return math.hypot(lamp.x - self.field.width / 2, lamp.y - self.field.height / 2)

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        return [self.point(lamp, t, p) for lamp in self.field.lamps]

    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        return p.color(0)


# -------------------------------------------------------------------- basics

class Static(Effect):
    pass


class Gradient(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        extent = abs(math.cos(p.angle)) * self.field.width + abs(math.sin(p.angle)) * self.field.height
        position = self.along(lamp, p) / max(extent, 1e-6) + 0.5
        count = len(p.colors)
        return palette_loop(p.colors, position * (count - 1) / count / p.zoom + t * 0.08)


class Breathing(Effect):
    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        cycle = t * 0.26
        level = (0.5 - 0.5 * math.cos(cycle * 2 * math.pi)) ** 1.6
        floor = (1 - p.intensity) * 0.35
        color = scale(p.colors[int(cycle) % len(p.colors)], floor + (1 - floor) * level)
        return [color] * len(self.field.lamps)


class Custom(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        return p.keys.get(lamp.id, p.color(0))


# ---------------------------------------------------------------------- flow

class Rainbow(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        return hsv(self.along(lamp, p) / (14 * p.zoom) - t * 0.16, 0.35 + 0.65 * p.intensity, 1.0)


class Spectrum(Effect):
    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        return [hsv(t * 0.07, 0.35 + 0.65 * p.intensity, 1.0)] * len(self.field.lamps)


class Wave(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        return palette_loop(p.colors, self.along(lamp, p) / (11 * p.zoom) - t * 0.2)


class Swirl(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        dx, dy = lamp.x - self.field.width / 2, (lamp.y - self.field.height / 2) * 1.6
        turn = math.atan2(dy, dx) / (2 * math.pi)
        twist = math.hypot(dx, dy) * (p.intensity - 0.5) * 0.12
        return palette_loop(p.colors, turn * max(1, round(1.5 / p.zoom)) + twist - t * 0.14)


class Plasma(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        x, y = lamp.x / p.zoom, lamp.y / p.zoom
        value = (math.sin(x * 0.52 + t * 0.9) + math.sin(y * 0.83 - t * 1.2)
                 + math.sin((x + y) * 0.37 + t * 0.6)
                 + math.sin(math.hypot(x - 8 / p.zoom, y - 3 / p.zoom) * 0.7 - t * 1.0))
        return palette_loop(p.colors, value / 8 * (0.6 + p.intensity * 1.4) + t * 0.03)


class Rings(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        dx, dy = lamp.x - self.field.width / 2, (lamp.y - self.field.height / 2) * 1.35
        return palette_loop(p.colors, math.hypot(dx, dy) / (7 * p.zoom) - t * 0.22)


# -------------------------------------------------------------------- nature

class Fire(Effect):
    """Flames rising from the bottom row; tips are brighter and flicker hardest."""

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        ember, flame, tip = p.color(0), p.color(1), p.color(2)
        gradient = [ember, flame, tip]
        reach = 0.3 + p.intensity * 0.8
        height = self.field.height
        out: list[RGB] = []
        for lamp in self.field.lamps:
            x = lamp.x / p.zoom
            up = 1 - lamp.y / height
            tongue = reach * (0.5 + 0.85 * fbm2(x * 0.42, t * 1.9))
            tongue += 0.1 * math.sin(x * 1.3 + t * 5.1) * noise2(x * 0.9, t * 2.7)
            turbulence = noise3(x * 0.8, lamp.y * 0.7 + t * 3.2, t * 1.3) - 0.5
            body = smoothstep(tongue + 0.13, tongue - 0.13, up + turbulence * 0.24)
            rel = clamp(up / max(tongue, 0.05))
            flicker = 1 - (0.08 + 0.55 * rel) * noise3(x * 1.7, lamp.y * 1.3 + t * 4.5, t * 6.0) ** 1.6
            color = scale(palette(gradient, rel ** 0.9), body ** 0.7 * (0.5 + 0.5 * rel) * flicker)
            glow = smoothstep(0.4, 0.0, up) * (0.22 + 0.2 * noise2(x * 1.1, t * 1.4))
            color = lighten(color, scale(ember, glow))
            spark = noise3(lamp.x * 2.3 + 11, lamp.y * 2.1 + t * 2.6, t * 3.1)
            if spark > 0.84 and up > tongue:
                color = lighten(color, scale(tip, (spark - 0.84) / 0.16 * 0.7))
            out.append(color)
        return out


class Ocean(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        deep, water, foam = p.color(0), p.color(1), p.color(2)
        x, y = lamp.x / p.zoom, lamp.y / p.zoom
        swell = noise3(x * 0.28, y * 0.5, t * 0.35)
        wave = 0.5 + 0.5 * math.sin(x * 0.62 + y * 0.35 - t * 1.25 + swell * 5.0)
        depth = lamp.y / self.field.height
        color = mix(deep, water, wave * (1 - depth * 0.45))
        crest = smoothstep(0.86 - p.intensity * 0.22, 1.0, wave) * (0.5 + 0.5 * noise3(x * 1.4, y * 1.4, t * 2.2))
        return mix(color, foam, crest)


class Aurora(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        x = lamp.x / p.zoom
        ny = lamp.y / self.field.height
        centre = 0.25 + 0.5 * noise2(x * 0.2 + t * 0.11, t * 0.07)
        curtain = math.exp(-((ny - centre) / (0.22 + 0.3 * p.intensity)) ** 2)
        rays = 0.55 + 0.45 * noise3(x * 1.3, ny * 0.6, t * 0.9)
        color = palette(p.colors, noise2(x * 0.16 - t * 0.09, ny * 0.5 + 7.0) * 1.25 - 0.12)
        return scale(color, 0.06 + 0.94 * curtain * rays)


class Lava(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        x, y = lamp.x / p.zoom, lamp.y / p.zoom
        heat = noise3(x * 0.3, y * 0.42, t * 0.16) * 0.7 + noise3(x * 0.8 + 9, y * 0.9, t * 0.3) * 0.3
        edge = 0.14 + (1 - p.intensity) * 0.22
        return palette(p.colors, smoothstep(0.5 - edge * 1.4, 0.5 + edge, heat))


class Storm(Effect):
    def __init__(self, field: Field, seed: int | None = None) -> None:
        super().__init__(field, seed)
        self.next_strike = 0.6
        self.strike_at = -10.0
        self.bolt: dict[int, float] = {}
        self.power = 1.0

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        cloud, rain, flash = p.color(0), p.color(1), p.color(2)
        if t >= self.next_strike or t < self.strike_at:
            self.strike_at = t
            self.next_strike = t + self.rng.uniform(0.6, 4.6 - 3.6 * p.intensity)
            x = self.rng.uniform(1.5, self.field.width - 1.5)
            self.bolt = {}
            for row in range(int(self.field.height) + 2):
                self.bolt[row] = x
                x = clamp(x + self.rng.uniform(-1.5, 1.5), 0.5, self.field.width - 0.5)
            self.power = self.rng.uniform(0.6, 1.0)
        age = t - self.strike_at
        envelope = (math.exp(-age * 9) + 0.75 * math.exp(-((age - 0.17) * 15) ** 2)) * self.power if age < 0.9 else 0.0
        out: list[RGB] = []
        for lamp in self.field.lamps:
            x = lamp.x / p.zoom
            color = scale(cloud, 0.18 + 0.55 * fbm2(x * 0.22 + t * 0.22, lamp.y * 0.35))
            column = int(lamp.x)
            fall = (t * 7.5 * (0.7 + 0.6 * _hash(column, 3)) + _hash(column, 9) * 23) % (self.field.height + 5)
            behind = fall - lamp.y
            if 0 <= behind < 1.7:
                color = add(color, scale(rain, (1 - behind / 1.7) * 0.8))
            if envelope > 0.004:
                near = abs(lamp.x - self.bolt.get(int(lamp.y), -99.0))
                color = add(color, scale(flash, envelope * (0.3 + math.exp(-(near / 0.8) ** 2))))
            out.append(color)
        return out


# ----------------------------------------------------------------- particles

class Matrix(Effect):
    def __init__(self, field: Field, seed: int | None = None) -> None:
        super().__init__(field, seed)
        self.drops: list[list[float]] = []  # column, head position, speed, trail length

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        trail, head = p.color(0), p.color(1)
        columns = int(self.field.width) + 1
        rate = columns * (0.25 + p.intensity * 1.6)
        if self.rng.random() < rate * dt:
            self.drops.append([self.rng.randrange(columns), -0.5, self.rng.uniform(4.5, 10.5),
                               self.rng.uniform(2.2, 5.5) * p.zoom])
        limit = self.field.height + 1
        for drop in self.drops:
            drop[1] += drop[2] * dt
        self.drops = [drop for drop in self.drops if drop[1] - drop[3] < limit]
        by_column: dict[int, list[list[float]]] = {}
        for drop in self.drops:
            by_column.setdefault(int(drop[0]), []).append(drop)
        out: list[RGB] = []
        for lamp in self.field.lamps:
            color = scale(trail, 0.035)
            for drop in by_column.get(int(lamp.x), ()):
                behind = drop[1] - lamp.y
                if 0 <= behind < drop[3]:
                    level = (1 - behind / drop[3]) ** 1.7
                    color = lighten(color, mix(scale(trail, level), head, smoothstep(0.75, 0.0, behind)))
            out.append(color)
        return out


class Starlight(Effect):
    def __init__(self, field: Field, seed: int | None = None) -> None:
        super().__init__(field, seed)
        self.stars: dict[int, list[float]] = {}  # lamp index -> age, lifetime, colour index

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        sky = p.color(0)
        tints = p.colors[1:] or [(1.0, 1.0, 1.0)]
        rate = 0.05 + p.intensity * 0.7
        out: list[RGB] = []
        for index, lamp in enumerate(self.field.lamps):
            star = self.stars.get(index)
            if star is None and self.rng.random() < rate * dt:
                star = self.stars[index] = [0.0, self.rng.uniform(0.7, 2.4), float(self.rng.randrange(len(tints)))]
            color = scale(sky, 0.1 + 0.08 * noise2(lamp.x * 0.5 + t * 0.2, lamp.y * 0.5))
            if star is not None:
                star[0] += dt
                progress = star[0] / star[1]
                if progress >= 1:
                    del self.stars[index]
                else:
                    glow = math.sin(math.pi * progress ** 0.6) ** 2
                    color = lighten(color, scale(tints[int(star[2]) % len(tints)], glow))
            out.append(color)
        return out


class Raindrops(Effect):
    def __init__(self, field: Field, seed: int | None = None) -> None:
        super().__init__(field, seed)
        self.drops: list[list[float]] = []  # x, y, age, colour index

    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        ground = p.color(0)
        tints = p.colors[1:] or [(1.0, 1.0, 1.0)]
        if self.rng.random() < (0.5 + p.intensity * 5.5) * dt:
            self.drops.append([self.rng.uniform(0, self.field.width), self.rng.uniform(0, self.field.height),
                               0.0, float(self.rng.randrange(len(tints)))])
        life = 1.5
        for drop in self.drops:
            drop[2] += dt
        self.drops = [drop for drop in self.drops if drop[2] < life]
        width = 0.75 * p.zoom
        out: list[RGB] = []
        for lamp in self.field.lamps:
            color = scale(ground, 0.14)
            for x, y, age, tint in self.drops:
                distance = math.hypot(lamp.x - x, (lamp.y - y) * 1.2)
                ring = math.exp(-((distance - age * 6.5) / width) ** 2) * (1 - age / life) ** 1.3
                if ring > 0.01:
                    color = add(color, scale(tints[int(tint) % len(tints)], ring))
            out.append(color)
        return out


class Comet(Effect):
    def render(self, t: float, dt: float, p: Params) -> list[RGB]:
        head, tail, ground = p.color(0), p.color(1), p.color(2)
        cos_a, sin_a = math.cos(p.angle), math.sin(p.angle)
        extent = abs(cos_a) * self.field.width + abs(sin_a) * self.field.height
        across = abs(sin_a) * self.field.width + abs(cos_a) * self.field.height
        tail_length = 3.5 + 5.5 * p.scale
        lap = extent + tail_length + 3
        count = 1 + round(p.intensity * 3)
        comets = []
        for index in range(count):
            travelled = t * 7.0 + index * lap / count
            lane = (_hash(int(travelled // lap), index, 5) - 0.5) * max(across - 1.2, 0.0)
            comets.append((travelled % lap - extent / 2 - 1.0, lane))
        out: list[RGB] = []
        for lamp in self.field.lamps:
            dx, dy = lamp.x - self.field.width / 2, lamp.y - self.field.height / 2
            forward, side = dx * cos_a + dy * sin_a, -dx * sin_a + dy * cos_a
            color = scale(ground, 0.12)
            for position, lane in comets:
                behind = position - forward
                body = math.exp(-behind / tail_length * 3.2) if behind >= 0 else math.exp(-(behind * 2.2) ** 2)
                level = body * math.exp(-((side - lane) / 1.05) ** 2)
                if level > 0.01:
                    color = lighten(color, scale(mix(tail, head, smoothstep(1.6, 0.0, abs(behind))), level))
            out.append(color)
        return out


class Heartbeat(Effect):
    def point(self, lamp: Lamp, t: float, p: Params) -> RGB:
        phase = (t * 0.85 - self.radius(lamp) * 0.03 * (0.4 + p.scale * 1.2)) % 1.0
        beat = math.exp(-((phase - 0.12) / 0.05) ** 2) + 0.6 * math.exp(-((phase - 0.36) / 0.06) ** 2)
        floor = 0.04 + (1 - p.intensity) * 0.3
        return scale(mix(p.color(0), p.color(1), beat * 0.8), floor + (1 - floor) * clamp(beat))


# -------------------------------------------------------------------- catalog

def _param(key: str, label: str, default: int) -> dict[str, Any]:
    return {"key": key, "label": label, "default": default}


def _speed(default: int = 50) -> dict[str, Any]:
    return _param("speed", "Geschwindigkeit", default)


def _angle(default: int = 0) -> dict[str, Any]:
    return _param("angle", "Richtung", default)


def _size(label: str = "Mustergröße", default: int = 50) -> dict[str, Any]:
    return _param("scale", label, default)


GROUPS = [
    {"id": "basic", "name": "Basis"},
    {"id": "flow", "name": "Fluss"},
    {"id": "nature", "name": "Natur"},
    {"id": "particles", "name": "Partikel"},
]

# ``fallback`` is the firmware mode the keyboard is left in when the app quits.
_CATALOG: list[dict[str, Any]] = [
    {"id": "static", "cls": Static, "name": "Einfarbig", "group": "basic", "fallback": "Static",
     "description": "Eine ruhige, gleichmäßige Farbe auf allen Tasten.",
     "colors": [("Farbe", "#8c6bff")], "params": []},
    {"id": "gradient", "cls": Gradient, "name": "Verlauf", "group": "basic", "fallback": "Static",
     "description": "Weicher Farbverlauf über das ganze Gerät – still oder langsam wandernd.",
     "colors": [("Farbe 1", "#ff5f8f"), ("Farbe 2", "#8c6bff"), ("Farbe 3", "#35c8ff")], "flex": True,
     "params": [_param("speed", "Drift", 0), _angle(0), _size("Streckung", 50)]},
    {"id": "breathing", "cls": Breathing, "name": "Atmen", "group": "basic", "fallback": "Breathing",
     "description": "Sanftes Ein- und Ausblenden. Mehrere Farben wechseln sich pro Atemzug ab.",
     "colors": [("Farbe 1", "#8c6bff"), ("Farbe 2", "#35c8ff")], "flex": True,
     "params": [_speed(45), _param("intensity", "Tiefe", 85)]},
    {"id": "custom", "cls": Custom, "name": "Eigene Tasten", "group": "basic", "fallback": "Static",
     "description": "Male jede Taste einzeln an – direkt in der Vorschau, mit Klicken und Ziehen.",
     "colors": [("Grundfarbe", "#000000")], "params": [], "paint": True},

    {"id": "rainbow", "cls": Rainbow, "name": "Regenbogenwelle", "group": "flow", "fallback": "Rainbow",
     "description": "Das volle Spektrum zieht als Welle über die Tasten.",
     "colors": [], "params": [_speed(45), _angle(0), _size("Wellenlänge", 50), _param("intensity", "Sättigung", 100)]},
    {"id": "spectrum", "cls": Spectrum, "name": "Farbzyklus", "group": "flow", "fallback": "Rainbow",
     "description": "Alle Tasten wandern gemeinsam durch das Farbspektrum.",
     "colors": [], "params": [_speed(40), _param("intensity", "Sättigung", 100)]},
    {"id": "wave", "cls": Wave, "name": "Farbwelle", "group": "flow", "fallback": "Static",
     "description": "Deine eigenen Farben rollen als weiche Welle in eine Richtung.",
     "colors": [("Farbe 1", "#ff4d8d"), ("Farbe 2", "#7a5cff"), ("Farbe 3", "#22d3ee")], "flex": True,
     "params": [_speed(50), _angle(0), _size("Wellenlänge", 50)]},
    {"id": "swirl", "cls": Swirl, "name": "Wirbel", "group": "flow", "fallback": "Static",
     "description": "Farben drehen sich wie ein Strudel um die Mitte der Tastatur.",
     "colors": [("Farbe 1", "#ff7a59"), ("Farbe 2", "#ff3d81"), ("Farbe 3", "#7a5cff"), ("Farbe 4", "#27d7c4")],
     "flex": True, "params": [_speed(50), _param("intensity", "Verdrehung", 70), _size("Armbreite", 50)]},
    {"id": "plasma", "cls": Plasma, "name": "Plasma", "group": "flow", "fallback": "Static",
     "description": "Organisch ineinanderfließende Farbfelder, wie flüssiges Licht.",
     "colors": [("Farbe 1", "#3b1cff"), ("Farbe 2", "#ff2fb3"), ("Farbe 3", "#ffb347"), ("Farbe 4", "#18e0c8")],
     "flex": True, "params": [_speed(45), _param("intensity", "Kontrast", 55), _size()]},
    {"id": "rings", "cls": Rings, "name": "Pulsringe", "group": "flow", "fallback": "Static",
     "description": "Farbringe breiten sich von der Mitte nach außen aus.",
     "colors": [("Farbe 1", "#0b1d5c"), ("Farbe 2", "#2f7bff"), ("Farbe 3", "#8ff0ff")], "flex": True,
     "params": [_speed(50), _size("Ringabstand", 50)]},

    {"id": "fire", "cls": Fire, "name": "Feuer", "group": "nature", "fallback": "Static",
     "description": "Flammen brennen von der untersten Reihe nach oben. Die Spitzen leuchten heller, "
                    "flackern und werfen Funken.",
     "colors": [("Glut", "#d21404"), ("Flamme", "#ff6a00"), ("Spitze", "#ffd95a")],
     "params": [_speed(50), _param("intensity", "Flammenhöhe", 60), _size("Flammenbreite", 50)]},
    {"id": "ocean", "cls": Ocean, "name": "Ozean", "group": "nature", "fallback": "Static",
     "description": "Dünung rollt über die Tasten, Schaumkronen blitzen auf den Wellenkämmen.",
     "colors": [("Tiefe", "#031a6b"), ("Wasser", "#0a8fd8"), ("Schaum", "#b9fff4")],
     "params": [_speed(45), _param("intensity", "Schaumkronen", 50), _size("Wellengröße", 50)]},
    {"id": "aurora", "cls": Aurora, "name": "Polarlicht", "group": "nature", "fallback": "Static",
     "description": "Schimmernde Lichtvorhänge wandern langsam über einen dunklen Himmel.",
     "colors": [("Farbe 1", "#17e88f"), ("Farbe 2", "#22c7e8"), ("Farbe 3", "#9a5cff")], "flex": True,
     "params": [_speed(45), _param("intensity", "Vorhanghöhe", 55), _size("Breite", 50)]},
    {"id": "lava", "cls": Lava, "name": "Lava", "group": "nature", "fallback": "Static",
     "description": "Zähe, glühende Ströme schieben sich unter einer dunklen Kruste hindurch.",
     "colors": [("Kruste", "#2a0303"), ("Lava", "#e82a05"), ("Glut", "#ffb21f")],
     "params": [_speed(45), _param("intensity", "Härte", 55), _size("Stromgröße", 50)]},
    {"id": "storm", "cls": Storm, "name": "Gewitter", "group": "nature", "fallback": "Static",
     "description": "Dunkle Wolken, fallender Regen – und Blitze, die quer über die Tastatur zucken.",
     "colors": [("Wolken", "#27306b"), ("Regen", "#3d7dff"), ("Blitz", "#eef4ff")],
     "params": [_speed(50), _param("intensity", "Blitzhäufigkeit", 50), _size("Wolkengröße", 50)]},

    {"id": "matrix", "cls": Matrix, "name": "Matrix-Regen", "group": "particles", "fallback": "Static",
     "description": "Leuchtende Tropfen fallen spaltenweise herab und ziehen einen Schweif hinter sich her.",
     "colors": [("Schweif", "#00e85a"), ("Kopf", "#d6ffe4")],
     "params": [_speed(50), _param("intensity", "Dichte", 50), _size("Schweiflänge", 50)]},
    {"id": "starlight", "cls": Starlight, "name": "Sternenhimmel", "group": "particles", "fallback": "Static",
     "description": "Einzelne Tasten funkeln zufällig auf und verglühen wieder.",
     "colors": [("Himmel", "#141a66"), ("Stern 1", "#ffffff"), ("Stern 2", "#8fd3ff"), ("Stern 3", "#ffd6a0")],
     "flex": True, "params": [_speed(50), _param("intensity", "Sternendichte", 45)]},
    {"id": "raindrops", "cls": Raindrops, "name": "Regentropfen", "group": "particles", "fallback": "Static",
     "description": "Tropfen fallen auf die Tastatur und schicken Ringe über die Nachbartasten.",
     "colors": [("Grund", "#0d2a6b"), ("Tropfen 1", "#38d6ff"), ("Tropfen 2", "#a98bff")], "flex": True,
     "params": [_speed(50), _param("intensity", "Tropfenmenge", 45), _size("Ringbreite", 50)]},
    {"id": "comet", "cls": Comet, "name": "Komet", "group": "particles", "fallback": "Static",
     "description": "Lichtpunkte schießen mit langem Schweif über die Tasten.",
     "colors": [("Kopf", "#ffffff"), ("Schweif", "#7a5cff"), ("Hintergrund", "#1a1440")],
     "params": [_speed(50), _angle(0), _param("intensity", "Anzahl", 35), _size("Schweiflänge", 50)]},
    {"id": "heartbeat", "cls": Heartbeat, "name": "Herzschlag", "group": "particles", "fallback": "Breathing",
     "description": "Ein doppelter Pulsschlag, der sich von der Mitte nach außen ausbreitet.",
     "colors": [("Puls", "#ff1f4b"), ("Spitze", "#ff9eb0")],
     "params": [_speed(50), _param("intensity", "Tiefe", 80), _size("Ausbreitung", 50)]},
]

EFFECTS: dict[str, dict[str, Any]] = {entry["id"]: entry for entry in _CATALOG}
DEFAULT_EFFECT = "aurora"
MAX_COLORS = 6
PARAM_KEYS = ("speed", "intensity", "scale", "angle")

# Effect names used by profiles written before the per-key engine existed.
LEGACY_EFFECTS = {"Static": "static", "Breathing": "breathing", "Rainbow": "rainbow", "Color cycle": "spectrum",
                  "Pulse": "breathing", "Ocean": "ocean", "Aurora": "aurora", "Fire": "fire", "Pastel flow": "spectrum"}


def default_settings(effect_id: str) -> dict[str, Any]:
    """The per-effect part of a config: colours and parameter values."""
    entry = EFFECTS[effect_id]
    settings: dict[str, Any] = {"colors": [color for _, color in entry["colors"]]}
    for param in entry["params"]:
        settings[param["key"]] = param["default"]
    if entry.get("paint"):
        settings["keys"] = {}
    return settings


def clean_settings(effect_id: str, raw: Any) -> dict[str, Any]:
    """Validate untrusted (file / UI) settings against the catalog entry."""
    entry = EFFECTS[effect_id]
    settings = default_settings(effect_id)
    if not isinstance(raw, dict):
        return settings
    colors = [rgb_to_hex(hex_to_rgb(color)) for color in raw.get("colors", []) if isinstance(color, str)]
    minimum = len(entry["colors"]) if not entry.get("flex") else min(2, len(entry["colors"]))
    limit = MAX_COLORS if entry.get("flex") else len(entry["colors"])
    if len(colors) >= max(minimum, 1 if entry["colors"] else 0):
        settings["colors"] = colors[:limit]
    if effect_id == "custom" and settings["colors"] == ["#1b1b2b"]:
        # Former default base colour; it left unpainted keys faintly lit.
        settings["colors"] = ["#000000"]
    for param in entry["params"]:
        try:
            top = 359 if param["key"] == "angle" else 100
            settings[param["key"]] = max(0, min(top, int(raw.get(param["key"], param["default"]))))
        except (TypeError, ValueError):
            pass
    if entry.get("paint") and isinstance(raw.get("keys"), dict):
        for led, color in raw["keys"].items():
            try:
                settings["keys"][str(int(led))] = rgb_to_hex(hex_to_rgb(color))
            except (TypeError, ValueError):
                continue
    return settings


def params_from(settings: dict[str, Any]) -> Params:
    colors = [hex_to_rgb(color) for color in settings.get("colors", [])] or [(1.0, 1.0, 1.0)]
    return Params(colors=colors,
                  intensity=settings.get("intensity", 50) / 100,
                  scale=settings.get("scale", 50) / 100,
                  angle=math.radians(settings.get("angle", 0)),
                  keys={int(led): hex_to_rgb(color) for led, color in settings.get("keys", {}).items()})


def speed_factor(speed: int) -> float:
    """Map the 0..100 speed slider to a time multiplier (50 -> 1.0)."""
    return (max(0, min(100, speed)) / 50) ** 1.6


def create(effect_id: str, field: Field, seed: int | None = None) -> Effect:
    return EFFECTS[effect_id]["cls"](field, seed)


THUMB_COLUMNS, THUMB_ROWS = 13, 5


def thumbnail(effect_id: str, settings: dict[str, Any] | None = None) -> list[str]:
    """A representative still frame on a coarse grid, for the gallery and profile cards."""
    if settings is None:
        settings = default_settings(effect_id)
        if effect_id == "custom":
            settings["colors"] = ["#232338"]
            accents = ["#ff4d8d", "#ffb347", "#35c8ff", "#7a5cff"]
            settings["keys"] = {str(index): accents[index % 4] for index in (15, 27, 28, 29, 36, 37, 49, 61)}
        field = Field.grid(THUMB_COLUMNS, THUMB_ROWS)
    elif effect_id == "custom":
        # Painted keys only make sense on the real layout: sample the nearest key per cell.
        keys = layout.azoth_keys()
        painted = params_from(settings)
        return [rgb_to_hex(painted.keys.get(min(keys, key=lambda k: (k.cx - cell.x) ** 2 + (k.cy - cell.y) ** 2).id,
                                             painted.color(0)))
                for cell in Field.grid(THUMB_COLUMNS, THUMB_ROWS).lamps]
    else:
        field = Field.grid(THUMB_COLUMNS, THUMB_ROWS)
    effect = create(effect_id, field, seed=7)
    params = params_from(settings)
    step = 1 / 20
    frame: list[RGB] = []
    for tick in range(70):
        frame = effect.render(2.0 + tick * step, step, params)
    return [rgb_to_hex(color) for color in frame]


def catalog() -> list[dict[str, Any]]:
    """Catalog in a QML-friendly shape, in the active language."""
    return [{"id": entry["id"], "name": tr(entry["name"]), "group": entry["group"],
             "description": tr(entry["description"]), "flex": bool(entry.get("flex")),
             "paint": bool(entry.get("paint")),
             "minColors": min(2, len(entry["colors"])) if entry.get("flex") else len(entry["colors"]),
             "colorLabels": [tr(label) for label, _ in entry["colors"]],
             "params": [{**param, "label": tr(param["label"])} for param in entry["params"]],
             "thumb": thumbnail(entry["id"])}
            for entry in _CATALOG]


def groups() -> list[dict[str, Any]]:
    return [{"id": group["id"], "name": tr(group["name"])} for group in GROUPS]
