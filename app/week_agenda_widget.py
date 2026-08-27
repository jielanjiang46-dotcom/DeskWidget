from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QMenu, QScrollArea, QSizeGrip, QVBoxLayout

from .plan.schedule_view import HourlyWeekCanvas
from .theme import rgba
from .widget_base import DesktopWidget


class WeekAgendaWidget(DesktopWidget, QFrame):
    widget_type = "week_agenda"

    def __init__(
        self, manager, position: QPoint | None = None,
        size: tuple[int, int] = (800, 460), always_on_top: bool = False,
    ) -> None:
        QFrame.__init__(self)
        self.init_desktop_widget(manager)
        self._drag_offset: QPoint | None = None
        self.setWindowTitle("一周日程")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(620, 320)
        self.resize(*size)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(16, 14, 16, 10)
        self.root.setSpacing(9)
        self.heading = QLabel()
        self.heading.setObjectName("agendaHeading")
        self.root.addWidget(self.heading)
        self.week_canvas = HourlyWeekCanvas(
            manager.plan_service, manager.course_service,
            respect_course_toggle=False,
        )
        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.week_scroll.setWidget(self.week_canvas)
        self.root.addWidget(self.week_scroll, 1)
        self.root.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        manager.plan_service.subscribe(self.refresh)
        manager.course_service.subscribe(self.refresh)
        if position is not None:
            self.move(position)
        self.enable_full_context_menu(self._show_context_menu)
        self.apply_theme()
        self.refresh()

    def refresh(self) -> None:
        start = date.today() - timedelta(days=date.today().weekday())
        self.heading.setText(
            f"本周日程  ·  {start:%m月%d日}—{(start + timedelta(days=6)):%m月%d日}"
        )
        self.week_canvas.set_week(start)

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, 92)
        self.setStyleSheet(f"""
            WeekAgendaWidget {{ background: {background}; border: 1px solid {theme.accent}; border-radius: 14px; color: #252A34; font-family: "Microsoft YaHei UI"; }}
            QLabel {{ background: transparent; }}
            QLabel#agendaHeading {{ color: {theme.accent_text}; font-size: 15px; font-weight: 700; }}
            QScrollArea {{ background: white; border: none; border-radius: 8px; }}
        """)

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("打开主界面", self.manager.main_window.show_panel)
        menu.addSeparator()
        top = QAction("窗口置顶", menu, checkable=True)
        top.setChecked(self.always_on_top)
        top.triggered.connect(self.set_always_on_top)
        menu.addAction(top)
        menu.addSeparator()
        menu.addAction("隐藏当前组件", self.hide_to_tray)
        menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self))
        menu.exec(pos)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self.manager.save_state()

    def state(self) -> dict[str, Any]:
        return {
            **self.common_state(), "width": self.width(), "height": self.height()
        }
