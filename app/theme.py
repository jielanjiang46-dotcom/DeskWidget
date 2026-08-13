import json
from dataclasses import dataclass

from .constants import SETTINGS_FILE


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    accent: str
    accent_hover: str
    accent_soft: str
    accent_text: str


THEMES = {
    "leaf": Theme("leaf", "浅叶绿", "#82AD72", "#709B62", "#EAF3E3", "#52734B"),
    "indigo": Theme("indigo", "靛蓝", "#6574E8", "#5868DB", "#E4E8FF", "#4859C8"),
    "blue": Theme("blue", "海蓝", "#3B82F6", "#2872E5", "#E2EEFF", "#2463C5"),
    "green": Theme("green", "青绿", "#2FA77A", "#258C67", "#DDF5EB", "#237C5E"),
    "orange": Theme("orange", "暖橙", "#E98547", "#D57337", "#FFF0E4", "#C8642F"),
    "rose": Theme("rose", "玫红", "#D96786", "#C75675", "#FBE5EC", "#B84968"),
}


class ThemeManager:
    def __init__(self) -> None:
        self._listeners = []
        settings = self._load()
        self.current_key = str(settings.get("theme", "indigo"))
        if self.current_key not in THEMES:
            self.current_key = "indigo"
        self.glass_enabled = bool(settings.get("glass_enabled", False))
        self.opacity = max(40, min(100, int(settings.get("opacity", 88))))

    @property
    def current(self) -> Theme:
        return THEMES.get(self.current_key, THEMES["indigo"])

    def subscribe(self, listener) -> None:
        self._listeners.append(listener)

    def set_theme(self, key: str) -> None:
        if key not in THEMES or key == self.current_key:
            return
        self.current_key = key
        self._save()
        for listener in tuple(self._listeners):
            listener(self.current)

    def set_glass(self, enabled: bool) -> None:
        if enabled == self.glass_enabled:
            return
        self.glass_enabled = enabled
        self._save()
        self._notify()

    def set_opacity(self, opacity: int) -> None:
        opacity = max(40, min(100, int(opacity)))
        if opacity == self.opacity:
            return
        self.opacity = opacity
        self._save()
        self._notify()

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener(self.current)

    def _load(self) -> dict:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError, AttributeError):
            return {}

    def _save(self) -> None:
        try:
            SETTINGS_FILE.write_text(
                json.dumps({
                    "theme": self.current_key,
                    "glass_enabled": self.glass_enabled,
                    "opacity": self.opacity,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass


def rgba(hex_color: str, opacity: int) -> str:
    color = hex_color.lstrip("#")
    red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
    alpha = round(255 * max(0, min(100, opacity)) / 100)
    return f"rgba({red}, {green}, {blue}, {alpha})"
