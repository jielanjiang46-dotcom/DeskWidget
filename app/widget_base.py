from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QCloseEvent

if TYPE_CHECKING:
    from .manager import WidgetManager


class DesktopWidget:
    """所有桌面组件共享的行为与持久化接口。"""

    widget_type: str

    def init_desktop_widget(self, manager: "WidgetManager") -> None:
        self.manager = manager
        self._allow_close = False
        # Desktop components stay visible when the main panel is hidden, but
        # should not create separate entries in the Windows taskbar.
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self._full_context_callback = None
        self._resize_edges = Qt.Edge(0)
        self._resize_start_global = QPoint()
        self._resize_start_geometry = QRect()
        self._resize_save_timer = QTimer(self)
        self._resize_save_timer.setSingleShot(True)
        self._resize_save_timer.setInterval(350)
        self._resize_save_timer.timeout.connect(self.manager.save_state)

    def enable_full_context_menu(self, callback) -> None:
        """Route mouse input from the entire component tree."""
        self._full_context_callback = callback
        self.installEventFilter(self)
        for child in self.findChildren(QObject):
            if hasattr(child, "installEventFilter"):
                child.installEventFilter(self)
                if hasattr(child, "setMouseTracking"):
                    child.setMouseTracking(True)

    def eventFilter(self, watched, event) -> bool:
        event_type = event.type()
        if event_type == QEvent.Type.ChildAdded:
            child = event.child()
            if child is not None and hasattr(child, "installEventFilter"):
                child.installEventFilter(self)
                QTimer.singleShot(0, lambda: self._install_descendant_filters(child))
        if self._full_context_callback is not None:
            if event_type == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    self._full_context_callback(event.globalPosition().toPoint())
                    return True
                if event.button() == Qt.MouseButton.LeftButton:
                    local = self.mapFromGlobal(event.globalPosition().toPoint())
                    edges = self._edges_at(local)
                    if edges:
                        self._resize_edges = edges
                        self._resize_start_global = event.globalPosition().toPoint()
                        self._resize_start_geometry = self.geometry()
                        return True
            elif event_type == QEvent.Type.MouseMove and self._resize_edges:
                self._perform_resize(event.globalPosition().toPoint())
                return True
            elif event_type == QEvent.Type.MouseButtonRelease and self._resize_edges:
                self._perform_resize(event.globalPosition().toPoint())
                self._resize_edges = Qt.Edge(0)
                self.manager.save_state()
                return True
            elif event_type == QEvent.Type.ContextMenu:
                return True
        return super().eventFilter(watched, event)

    def _install_descendant_filters(self, parent) -> None:
        if hasattr(parent, "installEventFilter"):
            parent.installEventFilter(self)
        for child in parent.findChildren(QObject):
            child.installEventFilter(self)
            if hasattr(child, "setMouseTracking"):
                child.setMouseTracking(True)

    def _edges_at(self, point: QPoint) -> Qt.Edges:
        margin = 12
        edges = Qt.Edge(0)
        if point.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif point.x() >= self.width() - margin:
            edges |= Qt.Edge.RightEdge
        if point.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif point.y() >= self.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _perform_resize(self, global_point: QPoint) -> None:
        delta = global_point - self._resize_start_global
        geometry = QRect(self._resize_start_geometry)
        minimum_width, minimum_height = self.minimumWidth(), self.minimumHeight()
        if self._resize_edges & Qt.Edge.RightEdge:
            geometry.setWidth(max(minimum_width, geometry.width() + delta.x()))
        if self._resize_edges & Qt.Edge.BottomEdge:
            geometry.setHeight(max(minimum_height, geometry.height() + delta.y()))
        if self._resize_edges & Qt.Edge.LeftEdge:
            right = geometry.right()
            geometry.setLeft(min(right - minimum_width + 1, geometry.left() + delta.x()))
        if self._resize_edges & Qt.Edge.TopEdge:
            bottom = geometry.bottom()
            geometry.setTop(min(bottom - minimum_height + 1, geometry.top() + delta.y()))
        self.setGeometry(geometry)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible():
            self._resize_save_timer.start()

    @property
    def always_on_top(self) -> bool:
        return bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

    def hide_to_tray(self) -> None:
        self.hide()
        self.manager.main_window.refresh_status()
        self.manager.show_tray_hint()

    def set_always_on_top(self, enabled: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()
        self.manager.save_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept() if self._allow_close else event.ignore()

    def common_state(self) -> dict[str, Any]:
        return {
            "type": self.widget_type,
            "x": self.x(),
            "y": self.y(),
            "always_on_top": self.always_on_top,
        }

    def state(self) -> dict[str, Any]:
        raise NotImplementedError


def restored_position(data: dict[str, Any]) -> QPoint:
    return QPoint(int(data.get("x", 100)), int(data.get("y", 100)))
