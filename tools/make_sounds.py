#!/usr/bin/env python3
"""Synthesize the interface sounds (soft mallet / glass tones) into assets/sounds.

Run after changing a recipe:  python3 tools/make_sounds.py
"""
from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "src" / "aura_studio" / "assets" / "sounds"

# Partials of a soft mallet tone: (frequency ratio, level, decay multiplier).
MALLET = ((1.0, 1.0, 1.0), (2.0, 0.28, 1.9), (3.01, 0.07, 3.2), (4.02, 0.04, 4.5))
GLASS = ((1.0, 1.0, 1.0), (2.76, 0.16, 2.4), (5.4, 0.05, 4.0))


def note(freq: float, start: float, decay: float, level: float = 1.0, partials=MALLET,
         glide: float = 0.0, attack: float = 0.004) -> list[tuple[int, float]]:
    """One struck tone as (sample index, value) pairs. ``glide`` bends the pitch in semitones."""
    length = int(decay * 7 * RATE)
    first = int(start * RATE)
    samples = []
    phases = [0.0] * len(partials)
    for index in range(length):
        t = index / RATE
        bend = 2 ** (glide * math.exp(-t / (decay * 0.6)) / 12)
        value = 0.0
        for number, (ratio, gain, damping) in enumerate(partials):
            phases[number] += 2 * math.pi * freq * ratio * bend / RATE
            value += math.sin(phases[number]) * gain * math.exp(-t * damping / decay)
        envelope = 0.5 - 0.5 * math.cos(math.pi * min(1.0, t / attack))
        samples.append((first + index, value * envelope * level))
    return samples


def breath(start: float, length: float, level: float, seed: int = 3) -> list[tuple[int, float]]:
    """A very soft band of filtered noise that gives a tap some texture."""
    rng = random.Random(seed)
    low = 0.0
    samples = []
    count = int(length * RATE)
    for index in range(count):
        low += (rng.uniform(-1, 1) - low) * 0.22
        envelope = math.sin(math.pi * index / count) ** 2
        samples.append((int(start * RATE) + index, low * envelope * level))
    return samples


def render(name: str, layers: list[list[tuple[int, float]]], peak: float) -> None:
    length = max(index for layer in layers for index, _ in layer) + 1
    buffer = [0.0] * length
    for layer in layers:
        for index, value in layer:
            buffer[index] += value
    # Gentle one-pole low-pass keeps everything round and unobtrusive.
    smooth = 0.0
    for index, value in enumerate(buffer):
        smooth += (value - smooth) * 0.55
        buffer[index] = smooth
    fade = int(0.012 * RATE)
    for index in range(fade):
        buffer[-1 - index] *= index / fade
    gain = peak / max(abs(value) for value in buffer)
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(b"".join(struct.pack("<hh", *(int(value * gain * 32767),) * 2) for value in buffer))
    print(f"{name}.wav  {length / RATE * 1000:.0f} ms")


C5, D5, E5, G5, A5, C6, E6, G6 = 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1318.5, 1568.0
G4, A4, E4, D4 = 392.0, 440.0, 329.63, 293.66

if __name__ == "__main__":
    # Light touch for buttons and list rows.
    render("tap", [note(C6, 0, 0.012, glide=3), breath(0, 0.018, 0.25)], 0.30)
    # Choosing an effect or colour: a warm, slightly longer pluck.
    render("select", [note(G5, 0, 0.035, glide=1.5), note(G6, 0.004, 0.02, 0.18)], 0.36)
    # Switching pages.
    render("nav", [note(E5, 0, 0.03), note(A5, 0.045, 0.04, 0.8)], 0.30)
    render("toggle_on", [note(E5, 0, 0.022), note(A5, 0.06, 0.04)], 0.34)
    render("toggle_off", [note(A5, 0, 0.022), note(E5, 0.06, 0.04, 0.9)], 0.32)
    # Painting a key: a tiny water-drop blip.
    render("paint", [note(E6, 0, 0.01, partials=GLASS, glide=-5, attack=0.002)], 0.22)
    render("success", [note(C5, 0, 0.05, 0.9, GLASS), note(E5, 0.07, 0.05, 0.9, GLASS),
                       note(G5, 0.14, 0.06, 0.95, GLASS), note(C6, 0.21, 0.09, 1.0, GLASS)], 0.40)
    render("error", [note(E4, 0, 0.045, 1.0), note(D4 * 2 ** (1 / 12), 0.11, 0.07, 1.0)], 0.38)
