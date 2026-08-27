from datetime import date, datetime, timedelta
from typing import Any

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QSizeGrip, QVBoxLayout,
)

from .theme import rgba
from .widget_base import DesktopWidget


class WeekAgendaWidget(DesktopWidget, QFrame):
    widget_type = "week_agenda"

    def __init__(
        self, manager, position: QPoint | None = None,
        size: tuple[int, int] = (760, 310), always_on_top: bool = False,
    ) -> None:
        QFrame.__init__(self)
        self.init_desktop_widget(manager)
        self._drag_offset: QPoint | None = None
        self.setWindowTitle("一周日程")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(560, 240)
        self.resize(*size)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(16, 14, 16, 10)
        self.root.setSpacing(9)
        self.heading = QLabel()
        self.heading.setObjectName("agendaHeading")
        self.root.addWidget(self.heading)
        self.days = QHBoxLayout()
        self.days.setSpacing(6)
        self.root.addLayout(self.days, 1)
        self.root.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        manager.plan_service.subscribe(self.refresh)
        manager.course_service.subscribe(self.refresh)
        if position is not None:
            self.move(position)
        self.enable_full_context_menu(self._show_context_menu)
        self.apply_theme()
        self.refresh()

    def refresh(self) -> None:
        while self.days.count():
            item = self.days.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        start = date.today() - timedelta(days=date.today().weekday())
        self.heading.setText(
            f"本周日程  ·  {start:%m月%d日}—{(start + timedelta(days=6)):%m月%d日}"
        )
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        for offset, weekday in enumerate(weekdays):
            day = start + timedelta(days=offset)
            card = QFrame()
            card.setObjectName("agendaToday" if day == date.today() else "agendaDay")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(4)
            title = QLabel(f"{weekday}  {day.day}")
            title.setObjectName("agendaDayTitle")
            layout.addWidget(title)
            entries: list[tuple[str, str, bool]] = []
            for course in self.manager.course_service.courses_on(day):
                detail = f"{course.start_time} {course.name}"
                if course.location:
                    detail += f"\n{course.location}"
                entries.append((course.start_time, detail, True))
            for task in self.manager.plan_service.items:
                if task.due_at and self._date(task.due_at) == day:
                    due = self._time(task.due_at)
                    entries.append((due, f"{'✓' if task.completed else '•'} {due} {task.title}", False))
            for _order, text, is_course in sorted(entries)[:5]:
                label = QLabel(text)
                label.setObjectName("agendaCourse" if is_course else "agendaTask")
                label.setWordWrap(True)
                layout.addWidget(label)
            if not entries:
                empty = QLabel("暂无安排")
                empty.setObjectName("agendaEmpty")
                layout.addWidget(empty)
            if len(entries) > 5:
                more = QLabel(f"还有 {len(entries) - 5} 项")
                more.setObjectName("agendaEmpty")
                layout.addWidget(more)
            layout.addStretch()
            self.days.addWidget(card, 1)

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, 92)
        self.setStyleSheet(f"""
            WeekAgendaWidget {{ background: {background}; border: 1px solid {theme.accent}; border-radius: 14px; color: #252A34; font-family: "Microsoft YaHei UI"; }}
            QLabel {{ background: transparent; }}
            QLabel#agendaHeading {{ color: {theme.accent_text}; font-size: 15px; font-weight: 700; }}
            QFrame#agendaDay {{ background: rgba(255,255,255,185); border: none; border-radius: 8px; }}
            QFrame#agendaToday {{ background: white; border: 1px solid {theme.accent}; border-radius: 8px; }}
            QLabel#agendaDayTitle {{ color: #555D69; font-size: 11px; font-weight: 700; }}
            QLabel#agendaCourse {{ background: {theme.accent_soft}; color: {theme.accent_text}; border-radius: 5px; padding: 4px; font-size: 9px; }}
            QLabel#agendaTask {{ color: #515865; font-size: 9px; padding: 3px; }}
            QLabel#agendaEmpty {{ color: #A0A6B0; font-size: 9px; }}
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

    @staticmethod
    def _date(value: str) -> date:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return date.max

    @staticmethod
    def _time(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return ""
