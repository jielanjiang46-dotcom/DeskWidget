from datetime import date, datetime, time, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .task_dialog import TaskDialog
from .schedule_view import ScheduleView


class PlanTaskRow(QFrame):
    def __init__(self, center: "PlanCenter", plan) -> None:
        super().__init__()
        self.center = center
        self.plan = plan
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        check = QCheckBox()
        check.setChecked(plan.completed)
        check.toggled.connect(
            lambda checked: center.manager.plan_service.set_completed(plan.id, checked)
        )
        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = QLabel(plan.title)
        title.setObjectName("completedTask" if plan.completed else "taskTitle")
        texts.addWidget(title)
        if plan.due_at:
            due = QLabel(center.format_plan_due(plan))
            due.setObjectName(
                "due" if plan.repeat_weekly else
                ("overdue" if center.is_overdue(plan.due_at) else "due")
            )
            texts.addWidget(due)
        layout.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(texts, 1)
        edit = QPushButton("编辑")
        edit.setObjectName("taskEdit")
        edit.setToolTip("修改任务内容和截止时间")
        edit.clicked.connect(lambda: center.edit_task(plan))
        layout.addWidget(edit, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda point: center.show_task_menu(plan, self.mapToGlobal(point))
        )

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.center.edit_task(self.plan)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class PlanCenter(QWidget):
    """完整计划管理视图；桌面计划组件共享同一数据服务。"""

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager
        self.filter_name = "today"
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.filters = QButtonGroup(self)
        self.filters.setExclusive(True)

        self.views = QStackedWidget()
        self.views.addWidget(self._build_list_view())
        self.views.addWidget(self._build_calendar_view())
        root.addWidget(self.views)
        self.manager.plan_service.subscribe(self.refresh)
        self.refresh()

    def _build_list_view(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title_row = QHBoxLayout()
        self.title = QLabel("今天")
        self.title.setObjectName("pageTitle")
        title_row.addWidget(self.title)
        title_row.addStretch()
        layout.addLayout(title_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(7)
        for key, label in (("today", "今天"), ("upcoming", "即将到期"), ("all", "全部"), ("completed", "已完成")):
            button = QPushButton(label)
            button.setObjectName("filterChip")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=key: self.set_filter(value))
            self.filters.addButton(button)
            filter_row.addWidget(button)
            if key == "today":
                button.setChecked(True)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        quick = QFrame()
        quick.setObjectName("quickAdd")
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(12, 5, 7, 5)
        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText("添加任务，按 Enter 保存")
        self.quick_input.returnPressed.connect(self.quick_add)
        detail = QPushButton("详细设置")
        detail.clicked.connect(lambda: self.manager.add_plan_item(self))
        quick_layout.addWidget(self.quick_input, 1)
        quick_layout.addWidget(detail)
        layout.addWidget(quick)

        self.summary = QLabel()
        self.summary.setObjectName("planSummary")
        layout.addWidget(self.summary)
        self.task_list = QListWidget()
        self.task_list.setSpacing(6)
        layout.addWidget(self.task_list, 1)
        return page

    def _build_calendar_view(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.schedule = ScheduleView(
            self.manager.plan_service, self.manager.course_service, self.edit_task,
            self.manager.add_plan_at,
        )
        layout.addWidget(self.schedule)
        return page

    def quick_add(self) -> None:
        title = self.quick_input.text().strip()
        if title:
            due = datetime.combine(date.today(), time(23, 59)).isoformat()
            self.manager.plan_service.add(title, due)
            self.quick_input.clear()

    def set_filter(self, name: str) -> None:
        self.filter_name = name
        self.views.setCurrentIndex(0)
        self.refresh()

    def show_tasks(self) -> None:
        self.views.setCurrentIndex(0)
        self.refresh()

    def show_calendar(self) -> None:
        self.views.setCurrentIndex(1)
        self.refresh()

    def filtered_items(self):
        end_today = datetime.combine(date.today(), time.max)
        end_week = end_today + timedelta(days=7)
        service = self.manager.plan_service
        items = service.items
        if self.filter_name == "today":
            return [
                x for x in items if not x.completed and
                (service.occurs_on(x, date.today()) or
                 (not x.repeat_weekly and x.due_at and self._dt(x.due_at) <= end_today))
            ]
        if self.filter_name == "upcoming":
            return [
                x for x in items if not x.completed and
                service.occurs_between(x, date.today(), end_week.date()) and
                not service.occurs_on(x, date.today())
            ]
        if self.filter_name == "completed":
            return [x for x in items if x.completed]
        return list(items)

    def refresh(self) -> None:
        labels = {"today": "今天", "upcoming": "即将到期", "all": "全部任务", "completed": "已完成"}
        self.title.setText(labels[self.filter_name])
        items = sorted(self.filtered_items(), key=lambda x: (x.completed, x.due_at or "9999"))
        self.summary.setText(f"{len(items)} 项任务")
        self._fill_list(self.task_list, items)
        self.schedule.refresh()

    def _fill_list(self, target: QListWidget, items) -> None:
        target.clear()
        for plan in items:
            row = PlanTaskRow(self, plan)
            item = QListWidgetItem(target)
            item.setSizeHint(row.sizeHint())
            target.setItemWidget(item, row)

    def show_task_menu(self, plan, pos) -> None:
        menu = QMenu(self)
        menu.addAction("编辑任务…", lambda: self.edit_task(plan))
        menu.addAction("删除任务", lambda: self.manager.plan_service.delete(plan.id))
        menu.exec(pos)

    def edit_task(self, plan) -> None:
        dialog = TaskDialog(self, plan)
        if dialog.exec() == dialog.DialogCode.Accepted:
            title, due, repeat_weekly = dialog.values()
            self.manager.plan_service.update(plan.id, title, due, repeat_weekly)

    @staticmethod
    def _dt(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.max

    def is_overdue(self, value: str) -> bool:
        return self._dt(value) < datetime.now()

    def format_due(self, value: str) -> str:
        due = self._dt(value)
        if due == datetime.max:
            return ""
        prefix = "已逾期 · " if due < datetime.now() else ""
        return prefix + due.strftime("%m月%d日 %H:%M")

    def format_plan_due(self, plan) -> str:
        if not plan.repeat_weekly:
            return self.format_due(plan.due_at)
        due = self._dt(plan.due_at)
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        return f"每周{weekdays[due.weekday()][1:]} {due:%H:%M}"
