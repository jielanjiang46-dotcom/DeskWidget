from datetime import datetime
from typing import Any

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizeGrip, QVBoxLayout

from ..widget_base import DesktopWidget
from ..theme import rgba


class TaskRow(QFrame):
    def __init__(self, plan, widget: "PlanWidget") -> None:
        super().__init__()
        self.setObjectName("taskRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(11, 9, 11, 9)
        row.setSpacing(10)
        check = QPushButton("✓" if plan.completed else "")
        check.setObjectName("taskCheckDone" if plan.completed else "taskCheck")
        check.setCheckable(True)
        check.setChecked(plan.completed)
        check.setFixedSize(20, 20)
        check.setCursor(Qt.CursorShape.PointingHandCursor)
        check.toggled.connect(
            lambda checked: widget.manager.plan_service.set_completed(plan.id, checked)
        )
        text = QVBoxLayout()
        text.setSpacing(3)
        title = QLabel(plan.title)
        title.setObjectName("doneTitle" if plan.completed else "taskTitle")
        title.setWordWrap(True)
        text.addWidget(title)
        due_text, due_kind = widget._plan_due_label(plan)
        if due_text:
            due = QLabel(due_text)
            due.setObjectName(due_kind)
            text.addWidget(due)
        row.addWidget(check, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(text, 1)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda point: widget._task_menu(plan.id, self.mapToGlobal(point))
        )


class PlanWidget(DesktopWidget, QFrame):
    widget_type = "plan"

    def __init__(self, manager, position: QPoint | None = None, size: tuple[int, int] = (350, 260), always_on_top: bool = False) -> None:
        QFrame.__init__(self)
        self.init_desktop_widget(manager)
        self._drag_offset = None
        self.setWindowTitle("今日计划")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(290, 190)
        self.resize(*size)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 18)
        self.layout.setSpacing(12)
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title_group.setSpacing(1)
        title = QLabel("今日计划")
        title.setObjectName("title")
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        title_group.addWidget(title)
        title_group.addWidget(self.summary)
        add = QPushButton("＋ 添加")
        add.setObjectName("addButton")
        add.setFixedSize(66, 30)
        add.clicked.connect(lambda _checked=False: manager.add_plan_item(self))
        header.addLayout(title_group)
        header.addStretch()
        header.addWidget(add)
        self.layout.addLayout(header)
        self.items_layout = QVBoxLayout()
        self.layout.addLayout(self.items_layout)
        self.empty_label = QLabel("今天还没有安排\n添加一件值得完成的小事吧")
        self.empty_label.setObjectName("empty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.empty_label)
        self.layout.addStretch()
        self.layout.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        self.setStyleSheet("""
            PlanWidget { background: #F8F9FC; border: 1px solid #E8EAF0; border-radius: 16px; }
            QLabel#title { font-size: 19px; font-weight: 700; color: #1F2430; }
            QLabel#summary { font-size: 11px; color: #9298A5; }
            QLabel#empty { color: #9BA1AC; line-height: 1.5; padding: 24px 4px; }
            QFrame#taskRow { background: rgba(255, 255, 255, 145); border: 1px solid rgba(255, 255, 255, 175); border-radius: 11px; }
            QLabel#taskTitle { background: transparent; color: #28322D; font-size: 13px; font-weight: 600; }
            QLabel#doneTitle { background: transparent; color: #929B96; font-size: 13px; text-decoration: line-through; }
            QLabel#dueNormal { background: transparent; color: #738079; font-size: 10px; }
            QLabel#dueUrgent { background: transparent; color: #C96B4B; font-size: 10px; font-weight: 600; }
            QPushButton#taskCheck, QPushButton#taskCheckDone { min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px; padding: 0; border-radius: 10px; font-size: 12px; font-weight: 700; }
            QPushButton#taskCheck { background: rgba(255,255,255,190); border: 1px solid #AEBBB3; color: transparent; }
            QPushButton#taskCheck:hover { border: 2px solid #82AD72; background: #F5FAF2; }
            QPushButton#taskCheckDone { background: #82AD72; border: 1px solid #82AD72; color: white; }
            QPushButton#addButton { border: none; border-radius: 8px; background: #EAEDFF; color: #5868D9; font-size: 12px; font-weight: 600; }
            QPushButton#addButton:hover { background: #DEE3FF; }
        """)
        self._base_style = self.styleSheet()
        self.apply_theme()
        manager.plan_service.subscribe(self.refresh)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60000)
        if position is not None:
            self.move(position)
        self.refresh()
        self.enable_full_context_menu(self._show_context_menu)

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, self.manager.theme.opacity) if self.manager.theme.glass_enabled else "#F8F9FC"
        base_style = self._base_style.replace("background: #F8F9FC", f"background: {background}")
        self.setStyleSheet(base_style + f"""
            QPushButton#taskCheck:hover {{ border-color: {theme.accent}; }}
            QPushButton#taskCheckDone {{ background: {theme.accent}; border-color: {theme.accent}; color: white; }}
            QPushButton#addButton {{ background: {theme.accent_soft}; color: {theme.accent_text}; }}
            QPushButton#addButton:hover {{ background: {theme.accent}; color: white; }}
        """)

    def refresh(self) -> None:
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        items = sorted(self.manager.plan_service.items, key=lambda x: (x.completed, x.due_at or "9999"))
        remaining = sum(not item.completed for item in items)
        self.summary.setText(f"{remaining} 项待完成" if items else "让今天更有条理")
        self.empty_label.setVisible(not items)
        for plan in items[:8]:
            self.items_layout.addWidget(TaskRow(plan, self))
        self.enable_full_context_menu(self._show_context_menu)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def _due_label(self, due_at: str | None) -> tuple[str, str]:
        if not due_at:
            return "", "dueNormal"
        try:
            seconds = (datetime.fromisoformat(due_at) - datetime.now()).total_seconds()
            if seconds < 0:
                return "已到期", "dueUrgent"
            elif seconds < 86400:
                return f"剩余 {max(1, int(seconds // 3600))} 小时", "dueUrgent"
            else:
                return f"剩余 {int(seconds // 86400)} 天", "dueNormal"
        except ValueError:
            return "", "dueNormal"

    def _plan_due_label(self, plan) -> tuple[str, str]:
        if not plan.repeat_weekly:
            return self._due_label(plan.due_at)
        try:
            due = datetime.fromisoformat(plan.due_at)
        except (TypeError, ValueError):
            return "", "dueNormal"
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        return f"每{weekdays[due.weekday()]} {due:%H:%M}", "dueNormal"

    def _task_menu(self, item_id: str, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("删除任务", lambda: self.manager.plan_service.delete(item_id))
        menu.exec(pos)

    def contextMenuEvent(self, event) -> None:
        self._show_context_menu(event.globalPos())

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("打开主界面", self.manager.main_window.show_panel)
        menu.addSeparator()
        menu.addAction("新建任务…", lambda: self.manager.add_plan_item(self))
        top = QAction("窗口置顶", menu, checkable=True)
        top.setChecked(self.always_on_top)
        top.triggered.connect(self.set_always_on_top)
        menu.addAction(top)
        menu.addSeparator()
        menu.addAction("隐藏当前组件", self.hide_to_tray)
        menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self))
        menu.exec(pos)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 45:
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

    def state(self) -> dict[str, Any]:
        return self.common_state() | {"width": self.width(), "height": self.height()}
