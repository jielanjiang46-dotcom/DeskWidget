from typing import Any

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QFrame, QMenu, QSizeGrip, QTextEdit, QVBoxLayout

from .theme import rgba
from .widget_base import DesktopWidget


NOTE_COLORS = {
    "暖黄": "#fff3b0",
    "薄荷": "#cdeedd",
    "天空": "#d9ecff",
    "淡粉": "#ffdce5",
    "灰白": "#f2f3f5",
}


class NoteWidget(DesktopWidget, QFrame):
    """可编辑并自动保存的桌面便签。"""

    widget_type = "note"

    def __init__(
        self,
        manager,
        text: str = "",
        color: str = "#fff3b0",
        position: QPoint | None = None,
        size: tuple[int, int] = (260, 220),
        always_on_top: bool = False,
    ) -> None:
        QFrame.__init__(self)
        self.init_desktop_widget(manager)
        self._drag_offset: QPoint | None = None
        self.color = color
        self.setWindowTitle("便签")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(180, 140)
        self.resize(*size)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 8, 8)
        self.editor = QTextEdit(self)
        self.editor.setPlainText(text)
        self.editor.setPlaceholderText("写点什么…")
        self.editor.setFrameStyle(QFrame.Shape.NoFrame)
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(
            lambda point: self._show_context_menu(self.editor.mapToGlobal(point))
        )
        layout.addWidget(self.editor)
        layout.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.manager.save_state)
        self.editor.textChanged.connect(self.save_timer.start)
        self._apply_color()
        if position is not None:
            self.move(position)
        self.enable_full_context_menu(self._show_context_menu)

    def _apply_color(self) -> None:
        theme = self.manager.theme.current
        background = rgba(self.color, self.manager.theme.opacity) if self.manager.theme.glass_enabled else self.color
        self.setStyleSheet(f"""
            NoteWidget {{ background: {background}; border: 1px solid rgba(30,35,45,18); border-radius: 14px; }}
            QTextEdit {{ background: transparent; color: #34373D; font-size: 14px; border: none; selection-background-color: {theme.accent}; }}
        """)

    def apply_theme(self) -> None:
        self._apply_color()

    def set_color(self, color: str) -> None:
        self.color = color
        self._apply_color()
        self.manager.save_state()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 12:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
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
        if self._drag_offset is not None:
            self._drag_offset = None
            self.manager.save_state()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("打开主界面", self.manager.main_window.show_panel)
        menu.addSeparator()
        menu.addAction("新建便签", lambda _checked=False: self.manager.create_note())
        color_menu = menu.addMenu("便签颜色")
        for name, color in NOTE_COLORS.items():
            action = QAction(name, color_menu, checkable=True)
            action.setChecked(color == self.color)
            action.triggered.connect(lambda _checked=False, value=color: self.set_color(value))
            color_menu.addAction(action)
        top_action = QAction("窗口置顶", menu, checkable=True)
        top_action.setChecked(self.always_on_top)
        top_action.triggered.connect(self.set_always_on_top)
        menu.addAction(top_action)
        menu.addSeparator()
        menu.addAction("隐藏当前组件", self.hide_to_tray)
        menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self))
        menu.addAction("退出全部", self.manager.quit_all)
        menu.exec(global_pos)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible():
            self.save_timer.start()

    def state(self) -> dict[str, Any]:
        return self.common_state() | {
            "text": self.editor.toPlainText(),
            "color": self.color,
            "width": self.width(),
            "height": self.height(),
        }
