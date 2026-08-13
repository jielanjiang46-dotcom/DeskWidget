from collections.abc import Callable
from typing import Any


WidgetFactory = Callable[[dict[str, Any]], object | None]


class WidgetRegistry:
    """桌面组件类型注册表。"""

    def __init__(self) -> None:
        self._factories: dict[str, WidgetFactory] = {}

    def register(self, widget_type: str, factory: WidgetFactory) -> None:
        if widget_type in self._factories:
            raise ValueError(f"组件类型已注册：{widget_type}")
        self._factories[widget_type] = factory

    def create(self, widget_type: str, data: dict[str, Any]) -> object | None:
        factory = self._factories.get(widget_type)
        return factory(data) if factory else None

    @property
    def types(self) -> tuple[str, ...]:
        return tuple(self._factories)

