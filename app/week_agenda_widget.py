from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizeGrip,
    QVBoxLayout,
)

from .plan.schedule_view import HourlyWeekCanvas
from .theme import rgba
from .widget_base import DesktopWidget


class ExpandLabel(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WeekAgendaWidget(DesktopWidget, QFrame):
    widget_type = "week_agenda"

    def __init__(
        self, manager, position: QPoint | None = None,
        size: tuple[int, int] = (800, 460), always_on_top: bool = False,
        anchor: str | None = None,
        collapsed: bool = False, expanded_height: int | None = None,
    ) -> None:
        QFrame.__init__(self)
        self.init_desktop_widget(manager)
        self._drag_offset: QPoint | None = None
        try:
            self.anchor = date.fromisoformat(anchor) if anchor else date.today()
        except ValueError:
            self.anchor = date.today()
        self._expanded_height = max(320, int(expanded_height or size[1]))
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
        self.header_controls = [self.heading]
        header = QHBoxLayout()
        header.setSpacing(6)
        header.addWidget(self.heading)
        header.addStretch()
        for text, callback in (
            ("‹", self.previous_week), ("今天", self.today), ("›", self.next_week)
        ):
            button = QPushButton(text)
            button.setObjectName("agendaNav")
            button.clicked.connect(callback)
            header.addWidget(button)
            self.header_controls.append(button)
        collapse = QPushButton("−")
        collapse.setObjectName("agendaNav")
        collapse.setToolTip("收起一周日程")
        collapse.clicked.connect(self.collapse)
        header.addWidget(collapse)
        self.header_controls.append(collapse)
        self.root.addLayout(header)
        self.week_canvas = HourlyWeekCanvas(
            manager.plan_service, manager.course_service,
            respect_course_toggle=False,
        )
        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.week_scroll.setWidget(self.week_canvas)
        self.root.addWidget(self.week_scroll, 1)
        self.size_grip = QSizeGrip(self)
        self.root.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignRight)
        self.expand_label = ExpandLabel("点击以查看本周课表")
        self.expand_label.setObjectName("agendaExpand")
        self.expand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.expand_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_label.clicked.connect(self.expand)
        self.expand_label.hide()
        self.root.addWidget(self.expand_label, 1)
        manager.plan_service.subscribe(self.refresh)
        manager.course_service.subscribe(self.refresh)
        if position is not None:
            self.move(position)
        self.enable_full_context_menu(self._show_context_menu)
        self.apply_theme()
        self.refresh()
        self.set_collapsed(collapsed, save=False, remember_height=False)

    def refresh(self) -> None:
        start = self.anchor - timedelta(days=self.anchor.weekday())
        current_start = date.today() - timedelta(days=date.today().weekday())
        prefix = "本周日程" if start == current_start else "一周日程"
        self.heading.setText(
            f"{prefix}  ·  {start:%m月%d日}—{(start + timedelta(days=6)):%m月%d日}"
        )
        self.week_canvas.set_week(start)

    def previous_week(self) -> None:
        self.anchor -= timedelta(days=7)
        self.refresh()
        self.manager.save_state()

    def next_week(self) -> None:
        self.anchor += timedelta(days=7)
        self.refresh()
        self.manager.save_state()

    def today(self) -> None:
        self.anchor = date.today()
        self.refresh()
        self.manager.save_state()

    def collapse(self) -> None:
        self.set_collapsed(True)

    def expand(self) -> None:
        self.set_collapsed(False)

    def set_collapsed(
        self, collapsed: bool, save: bool = True, remember_height: bool = True
    ) -> None:
        if collapsed:
            if remember_height and self.height() > 44:
                self._expanded_height = self.height()
            for control in self.header_controls:
                control.hide()
            self.week_scroll.hide()
            self.size_grip.hide()
            self.expand_label.show()
            self.setMinimumHeight(44)
            self.setMaximumHeight(44)
            self.resize(self.width(), 44)
        else:
            self.setMaximumHeight(16777215)
            self.setMinimumSize(620, 320)
            self.expand_label.hide()
            for control in self.header_controls:
                control.show()
            self.week_scroll.show()
            self.size_grip.show()
            self.resize(self.width(), self._expanded_height)
        self._collapsed = collapsed
        if save:
            self.manager.save_state()

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, 92)
        self.setStyleSheet(f"""
            WeekAgendaWidget {{ background: {background}; border: 1px solid {theme.accent}; border-radius: 14px; color: #252A34; font-family: "Microsoft YaHei UI"; }}
            QLabel {{ background: transparent; }}
            QLabel#agendaHeading {{ color: {theme.accent_text}; font-size: 15px; font-weight: 700; }}
            QPushButton#agendaNav {{ min-width: 34px; min-height: 25px; max-height: 25px; padding: 0 7px; background: white; color: #59616D; border: 1px solid #DDE1E8; border-radius: 6px; }}
            QPushButton#agendaNav:hover {{ border-color: {theme.accent}; color: {theme.accent_text}; }}
            QLabel#agendaExpand {{ color: {theme.accent_text}; font-size: 13px; font-weight: 700; }}
            QLabel#agendaExpand:hover {{ color: {theme.accent}; }}
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
            **self.common_state(), "width": self.width(), "height": self.height(),
            "anchor": self.anchor.isoformat(), "collapsed": self._collapsed,
            "expanded_height": self._expanded_height,
        }
