"""One render thread per device: effect -> frame -> HID link (+ UI preview)."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from . import effects, hid
from .devices import Device
from .i18n import tr

FADE_SECONDS = 0.45
RETRY_SECONDS = 3.0


class Runner(threading.Thread):
    def __init__(self, device: Device, field: effects.Field, config: dict[str, Any], fps: int,
                 on_frame: Callable[[str, list[str]], None], on_error: Callable[[str, str], None]) -> None:
        super().__init__(name=f"AuraRunner-{device.name}", daemon=True)
        self.device = device
        self.field = field
        self.fps = fps
        self.preview = False
        self.hold = False  # True while something else (the OLED upload) needs the device
        self.sleeping = False  # lights faded out after inactivity
        self.fallback_on_stop = True
        self._config = config
        self._on_frame = on_frame
        self._on_error = on_error
        self._stop_event = threading.Event()
        self._logger = hid.app_logger()

    def configure(self, config: dict[str, Any]) -> None:
        # Swapping the reference is atomic; the render loop picks it up next frame.
        self._config = config

    def stop(self, fallback: bool = True) -> None:
        self.fallback_on_stop = fallback
        self._stop_event.set()
        if self.is_alive() and self is not threading.current_thread():
            self.join(timeout=2.0)

    def _fallback(self, config: dict[str, Any]) -> tuple[str, hid.Color, int] | None:
        if not self.fallback_on_stop:
            return None
        colors = config.get("colors") or ["#ffffff"]
        brightness = config.get("brightness", 100) if config.get("enabled", True) else 0
        return (effects.EFFECTS[config["effect"]]["fallback"],
                effects.rgb_to_bytes(effects.hex_to_rgb(colors[min(1, len(colors) - 1)])), brightness)

    def run(self) -> None:
        link = self.device.link()
        last_error = ""
        while not self._stop_event.is_set():
            try:
                link.open()
                self._logger.info("Runner started device=%s effect=%s", self.device.name, self._config["effect"])
                self._render_loop(link)
            except OSError as exc:
                message = (tr("Keine Berechtigung für {path}. Installiere die udev-Regel aus packaging/99-aura-studio.rules.")
                           .format(path=self.device.path) if isinstance(exc, PermissionError)
                           else tr("{name}: Verbindung unterbrochen ({error}).").format(name=self.device.name, error=exc))
                if message != last_error:
                    self._logger.exception("Runner failed device=%s", self.device.name)
                    self._on_error(self.device.id, message)
                    last_error = message
            except Exception:
                self._logger.exception("Runner crashed device=%s", self.device.name)
                self._on_error(self.device.id, tr("{name}: Effekt wurde unerwartet beendet.").format(name=self.device.name))
                return
            finally:
                link.close(self._fallback(self._config) if self._stop_event.is_set() else None)
            self._stop_event.wait(RETRY_SECONDS)

    def _render_loop(self, link: hid.Link) -> None:
        lamps = self.field.lamps
        seen: dict[str, Any] | None = None
        effect: effects.Effect | None = None
        params: effects.Params | None = None
        previous: tuple[effects.Effect, effects.Params] | None = None
        fade = 1.0
        clock = 0.0
        level = 0.0
        last = time.monotonic()
        while not self._stop_event.is_set():
            config = self._config
            if config is not seen:
                if seen is None or config["effect"] != seen["effect"]:
                    if effect is not None and params is not None:
                        previous, fade = (effect, params), 0.0
                    effect = effects.create(config["effect"], self.field)
                params = effects.params_from(config)
                seen = config
            now = time.monotonic()
            elapsed = min(now - last, 0.25)
            last = now
            step = elapsed * effects.speed_factor(config.get("speed", 50))
            clock += step
            frame = effect.render(clock, step, params)
            if previous is not None:
                fade += elapsed / FADE_SECONDS
                if fade >= 1:
                    previous = None
                else:
                    old = previous[0].render(clock, step, previous[1])
                    amount = effects.smoothstep(0.0, 1.0, fade)
                    frame = [effects.mix(a, b, amount) for a, b in zip(old, frame)]
            # Brightness and power changes glide instead of snapping.
            target = config.get("brightness", 100) / 100 if config.get("enabled", True) and not self.sleeping else 0.0
            level += (target - level) * min(1.0, elapsed * (2.5 if self.sleeping else 9))
            if abs(target - level) < 0.004:
                level = target
            if not self.hold:
                link.send({lamp.id: effects.rgb_to_bytes(effects.scale(color, level)) for lamp, color in zip(lamps, frame)})
            if self.preview:
                shown = level ** 0.6
                self._on_frame(self.device.id, [effects.rgb_to_hex(effects.scale(color, shown)) for color in frame])
            period = 1 / max(1.0, min(self.fps, link.fps_limit))
            self._stop_event.wait(max(0.002, period - (time.monotonic() - now)))
