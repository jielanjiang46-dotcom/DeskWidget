from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSizeGrip

from .widget_base import DesktopWidget

if TYPE_CHECKING:
    from .manager import WidgetManager


class ImageWidget(DesktopWidget, QLabel):
    """一个可独立拖动、缩放和更换图片的桌面组件。"""

    def __init__(
        self,
        manager: "WidgetManager",
        image_path: Path,
        scale: float | None = None,
        position: QPoint | None = None,
        always_on_top: bool = False,
    ) -> None:
        super().__init__()
        self.init_desktop_widget(manager)
        self.image_path = image_path.resolve()
        self._pixmap = QPixmap()
        self._scale = scale or 1.0
        self._initial_scale = 1.0
        self._drag_offset: QPoint | None = None
        self._updating_pixmap = False
        self.widget_type = "image"

        self.setWindowTitle(self.image_path.name)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("左键拖动 · 滚轮缩放 · 双击切换原始大小 · 右键管理")

        self.set_image(self.image_path, keep_scale=scale is not None)
        if position is not None:
            self.move(position)
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.move(self.width() - 18, self.height() - 18)
        self.size_grip.raise_()
        self.enable_full_context_menu(self._show_context_menu)

    def set_image(self, image_path: Path, keep_scale: bool = False) -> None:
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            raise ValueError(f"无法加载图片：{image_path}")
        self.image_path = image_path.resolve()
        self._pixmap = pixmap
        self.setWindowTitle(self.image_path.name)
        self._calculate_fit_scale()
        if not keep_scale:
            self._scale = self._initial_scale
        self._update_pixmap()

    def _calculate_fit_scale(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self._initial_scale = 1.0
            return
        available = screen.availableGeometry().size() * 0.8
        self._initial_scale = min(
            1.0,
            available.width() / self._pixmap.width(),
            available.height() / self._pixmap.height(),
        )

    def _update_pixmap(self) -> None:
        self._updating_pixmap = True
        pixel_ratio = self.devicePixelRatioF()
        logical_size = self._pixmap.size() * self._scale
        scaled = self._pixmap.scaled(
            logical_size * pixel_ratio,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(pixel_ratio)
        self.setPixmap(scaled)
        self.resize(logical_size)
        self._updating_pixmap = False
        if hasattr(self, "size_grip"):
            self.size_grip.move(self.width() - 18, self.height() - 18)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.manager.save_state()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale = self._initial_scale if abs(self._scale - 1.0) < 0.01 else 1.0
            self._update_pixmap()
            self.manager.save_state()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self._scale = max(0.1, min(3.0, self._scale * factor))
        self._update_pixmap()
        self.manager.save_state()
        event.accept()

    def contextMenuEvent(self, event) -> None:
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("打开主界面", self.manager.main_window.show_panel)
        menu.addSeparator()
        menu.addAction("新增图片组件…", self.manager.add_from_dialog)
        menu.addAction("更换这张图片…", lambda: self.manager.change_image(self))
        menu.addAction("复制这个组件", lambda: self.manager.duplicate_widget(self))
        menu.addSeparator()
        menu.addAction("适合屏幕", self.reset_scale)
        menu.addAction("原始大小（最清晰）", self.show_original_size)

        top_action = QAction("窗口置顶", menu, checkable=True)
        top_action.setChecked(self.always_on_top)
        top_action.triggered.connect(self.set_always_on_top)
        menu.addAction(top_action)

        menu.addSeparator()
        menu.addAction("隐藏当前组件", self.hide_to_tray)
        menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self))
        menu.addAction("退出全部", self.manager.quit_all)
        menu.exec(pos)

    def resizeEvent(self, event) -> None:
        QLabel.resizeEvent(self, event)
        if hasattr(self, "size_grip"):
            self.size_grip.move(self.width() - 18, self.height() - 18)
        if not self._updating_pixmap and not self._pixmap.isNull():
            new_scale = min(
                self.width() / self._pixmap.width(),
                self.height() / self._pixmap.height(),
            )
            self._scale = max(0.1, min(3.0, new_scale))
            self._update_pixmap()
            if self.isVisible():
                self._resize_save_timer.start()

    def reset_scale(self) -> None:
        self._calculate_fit_scale()
        self._scale = self._initial_scale
        self._update_pixmap()
        self.manager.save_state()

    def show_original_size(self) -> None:
        self._scale = 1.0
        self._update_pixmap()
        self.manager.save_state()

    def state(self) -> dict:
        return self.common_state() | {
            "image": str(self.image_path),
            "scale": round(self._scale, 4),
        }
