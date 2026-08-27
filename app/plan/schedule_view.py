import calendar
from datetime import date, datetime, timedelta

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class HourlyWeekCanvas(QWidget):
    """Seven-day calendar laid out on an hourly vertical timeline."""

    start_hour = 7
    end_hour = 22
    hour_height = 64
    header_height = 52
    time_width = 58

    def __init__(
        self, plan_service, course_service, respect_course_toggle: bool = True
    ) -> None:
        super().__init__()
        self.plan_service = plan_service
        self.course_service = course_service
        self.respect_course_toggle = respect_course_toggle
        self.start = date.today()
        self.setMinimumWidth(690)
        self.setFixedHeight(
            self.header_height + (self.end_hour - self.start_hour) * self.hour_height + 2
        )

    def set_week(self, start: date) -> None:
        self.start = start
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        day_width = (self.width() - self.time_width) / 7
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

        today_column = (date.today() - self.start).days
        if 0 <= today_column < 7:
            painter.fillRect(
                QRectF(
                    self.time_width + today_column * day_width + 1, 1,
                    day_width - 2, self.height() - 2,
                ),
                QColor("#F6F8FF"),
            )

        painter.setPen(QPen(QColor("#E6E9EF"), 1))
        painter.drawLine(0, self.header_height, self.width(), self.header_height)
        for column in range(8):
            x = self.time_width + column * day_width
            painter.drawLine(int(x), 0, int(x), self.height())
        for hour in range(self.start_hour, self.end_hour + 1):
            y = self.header_height + (hour - self.start_hour) * self.hour_height
            painter.drawLine(self.time_width, y, self.width(), y)
            painter.setPen(QColor("#9299A4"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(
                QRectF(0, y - 11, self.time_width - 8, 22),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{hour:02d}:00",
            )
            painter.setPen(QPen(QColor("#E6E9EF"), 1))

        for column, weekday in enumerate(weekdays):
            day = self.start + timedelta(days=column)
            x = self.time_width + column * day_width
            painter.setPen(QColor("#69717E"))
            painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.DemiBold))
            painter.drawText(
                QRectF(x, 4, day_width, 21), Qt.AlignmentFlag.AlignCenter, weekday
            )
            painter.setPen(QColor("#252A34"))
            painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
            painter.drawText(
                QRectF(x, 23, day_width, 25), Qt.AlignmentFlag.AlignCenter,
                f"{day.month}/{day.day}",
            )
            self._paint_day_events(painter, day, x, day_width)

        now = datetime.now()
        if self.start <= now.date() <= self.start + timedelta(days=6):
            minute = now.hour * 60 + now.minute
            if self.start_hour * 60 <= minute <= self.end_hour * 60:
                column = (now.date() - self.start).days
                x = self.time_width + column * day_width
                y = self._minute_y(minute)
                painter.setPen(QPen(QColor("#E75B52"), 2))
                painter.drawLine(int(x), int(y), int(x + day_width), int(y))

    def _paint_day_events(
        self, painter: QPainter, day: date, x: float, day_width: float
    ) -> None:
        events: list[tuple[int, int, str, str, str]] = []
        if not self.respect_course_toggle or self.course_service.show_in_calendar:
            for course in self.course_service.courses_on(day):
                start = self._minutes(course.start_time)
                end = self._minutes(course.end_time)
                detail = course.name
                if course.location:
                    detail += f"\n{course.location}"
                events.append((start, end, detail, "#DCEAFF", "#285F9C"))
        for task in self.plan_service.items:
            if not task.due_at:
                continue
            try:
                due = datetime.fromisoformat(task.due_at)
            except ValueError:
                continue
            if due.date() == day:
                minute = due.hour * 60 + due.minute
                title = ("✓ " if task.completed else "• ") + task.title
                events.append((minute, minute + 30, title, "#E8EAFE", "#4859C8"))

        for start, end, text, background, foreground in sorted(events):
            visible_start = max(start, self.start_hour * 60)
            visible_end = min(end, self.end_hour * 60)
            if visible_end <= visible_start:
                continue
            top = self._minute_y(visible_start) + 2
            bottom = self._minute_y(visible_end) - 2
            rect = QRectF(x + 4, top, day_width - 8, max(24, bottom - top))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(background))
            painter.drawRoundedRect(rect, 5, 5)
            painter.setPen(QColor(foreground))
            painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.DemiBold))
            painter.drawText(
                rect.adjusted(6, 4, -4, -3),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop |
                Qt.TextFlag.TextWordWrap,
                text,
            )

    def _minute_y(self, minute: int) -> float:
        return self.header_height + (
            minute - self.start_hour * 60
        ) * self.hour_height / 60

    @staticmethod
    def _minutes(value: str) -> int:
        hour, minute = (int(part) for part in value.split(":", 1))
        return hour * 60 + minute


class TaskLabel(QLabel):
    """保留日历任务标签外观，同时提供清晰的点击编辑入口。"""

    clicked = Signal()

    def __init__(self, text: str, task, edit_task, parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{task.title}\n点击编辑任务")
        if edit_task is not None:
            self.clicked.connect(lambda: edit_task(task))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ScheduleView(QWidget):
    """在周、月、年三个尺度内直接展示任务。"""

    def __init__(self, service, course_service, edit_task=None) -> None:
        super().__init__()
        self.service = service
        self.course_service = course_service
        self.edit_task = edit_task
        self.mode = "month"
        self.anchor = date.today()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        self.period = QLabel()
        self.period.setObjectName("pageTitle")
        header.addWidget(self.period)
        header.addStretch()
        self.course_toggle = QCheckBox("显示课表")
        self.course_toggle.setChecked(course_service.show_in_calendar)
        self.course_toggle.toggled.connect(course_service.set_show_in_calendar)
        header.addWidget(self.course_toggle)
        modes = QButtonGroup(self)
        for key, text in (("week", "周"), ("month", "月"), ("year", "年")):
            button = QPushButton(text)
            button.setObjectName("filterChip")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=key: self.set_mode(value))
            modes.addButton(button)
            header.addWidget(button)
            if key == "month": button.setChecked(True)
        for text, callback in (("‹", self.previous), ("今天", self.today), ("›", self.next)):
            button = QPushButton(text)
            button.clicked.connect(callback)
            header.addWidget(button)
        root.addLayout(header)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(True)
        self.table.setWordWrap(True)
        root.addWidget(self.table)
        self.week_canvas = HourlyWeekCanvas(service, course_service)
        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.week_scroll.setWidget(self.week_canvas)
        self.week_scroll.hide()
        root.addWidget(self.week_scroll)
        self.course_service.subscribe(self._course_changed)
        self.refresh()

    def _course_changed(self) -> None:
        self.course_toggle.blockSignals(True)
        self.course_toggle.setChecked(self.course_service.show_in_calendar)
        self.course_toggle.blockSignals(False)
        self.refresh()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.refresh()

    def previous(self) -> None:
        if self.mode == "week": self.anchor -= timedelta(days=7)
        elif self.mode == "month": self.anchor = self._shift_month(-1)
        else: self.anchor = self.anchor.replace(year=self.anchor.year - 1)
        self.refresh()

    def next(self) -> None:
        if self.mode == "week": self.anchor += timedelta(days=7)
        elif self.mode == "month": self.anchor = self._shift_month(1)
        else: self.anchor = self.anchor.replace(year=self.anchor.year + 1)
        self.refresh()

    def today(self) -> None:
        self.anchor = date.today()
        self.refresh()

    def refresh(self) -> None:
        is_week = self.mode == "week"
        self.table.setVisible(not is_week)
        self.week_scroll.setVisible(is_week)
        if is_week:
            self._week()
            return
        self._clear_table()
        if self.mode == "month": self._month()
        else: self._year()

    def _clear_table(self) -> None:
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

    def _week(self) -> None:
        start = self.anchor - timedelta(days=self.anchor.weekday())
        self.period.setText(f"{start:%Y年%m月%d日} — {(start + timedelta(days=6)):%m月%d日}")
        self.week_canvas.set_week(start)

    def _month(self) -> None:
        self.period.setText(f"{self.anchor:%Y年%m月}")
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self.anchor.year, self.anchor.month)
        self.table.setRowCount(len(weeks)); self.table.setColumnCount(7)
        self.table.horizontalHeader().show()
        self.table.setMaximumHeight(16777215)
        self.table.setHorizontalHeaderLabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                self.table.setCellWidget(
                    row, col, self._month_card(day, day.month == self.anchor.month)
                )
        self.table.horizontalHeader().setSectionResizeMode(self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(108)

    def _year(self) -> None:
        self.period.setText(f"{self.anchor.year}年")
        self.table.setRowCount(3); self.table.setColumnCount(4)
        self.table.horizontalHeader().hide()
        self.table.setMaximumHeight(16777215)
        self.table.setHorizontalHeaderLabels([])
        for month in range(1, 13):
            tasks = [x for x in self.service.items if x.due_at and self._date(x.due_at).year == self.anchor.year and self._date(x.due_at).month == month]
            courses = []
            if self.course_service.show_in_calendar:
                days = calendar.monthrange(self.anchor.year, month)[1]
                for number in range(1, days + 1):
                    courses.extend(
                        self.course_service.courses_on(date(self.anchor.year, month, number))
                    )
            self.table.setCellWidget(
                (month - 1) // 4,
                (month - 1) % 4,
                self._year_card(month, tasks, courses),
            )
        self.table.horizontalHeader().setSectionResizeMode(self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(145)

    def _day_item(self, day: date, include_date: bool) -> QTableWidgetItem:
        tasks = [x for x in self.service.items if x.due_at and self._date(x.due_at) == day]
        lines = [str(day.day)] if include_date else []
        lines.extend(("✓ " if x.completed else "• ") + x.title for x in tasks[:4])
        if len(tasks) > 4: lines.append(f"还有 {len(tasks)-4} 项…")
        item = QTableWidgetItem("\n".join(lines))
        item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        return item

    def _week_card(self, day: date) -> QWidget:
        card = QFrame()
        card.setObjectName("weekCardToday" if day == date.today() else "weekCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        weekday = QLabel(weekdays[day.weekday()])
        weekday.setObjectName("weekDay")
        number = QLabel(str(day.day))
        number.setObjectName("weekNumber")
        layout.addWidget(weekday)
        layout.addWidget(number)
        tasks = [x for x in self.service.items if x.due_at and self._date(x.due_at) == day]
        courses = self._courses(day)
        if not tasks and not courses:
            empty = QLabel("暂无安排")
            empty.setObjectName("weekEmpty")
            layout.addWidget(empty)
        for course in courses[:3]:
            label = QLabel(f"{course.start_time} {course.name}")
            label.setObjectName("weekCourse")
            label.setWordWrap(True)
            label.setToolTip(self._course_tooltip(course))
            layout.addWidget(label)
        for task in tasks[:3]:
            label = self._task_label(task)
            label.setObjectName("weekTaskDone" if task.completed else "weekTask")
            label.setWordWrap(True)
            layout.addWidget(label)
        hidden = max(0, len(courses) - 3) + max(0, len(tasks) - 3)
        if hidden:
            more = QLabel(f"还有 {hidden} 项")
            more.setObjectName("weekEmpty")
            layout.addWidget(more)
        layout.addStretch()
        return card

    def _month_card(self, day: date, in_month: bool) -> QWidget:
        card = QFrame()
        if day == date.today():
            card.setObjectName("monthCardToday")
        elif in_month:
            card.setObjectName("monthCard")
        else:
            card.setObjectName("monthCardMuted")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(4)
        number = QLabel(str(day.day))
        number.setObjectName("monthNumberMuted" if not in_month else "monthNumber")
        layout.addWidget(number, 0, Qt.AlignmentFlag.AlignLeft)
        tasks = [x for x in self.service.items if x.due_at and self._date(x.due_at) == day]
        courses = self._courses(day)
        for course in courses[:1]:
            label = QLabel(f"{course.start_time} {course.name}")
            label.setObjectName("monthCourse")
            label.setWordWrap(False)
            label.setToolTip(self._course_tooltip(course))
            layout.addWidget(label)
        for task in tasks[:2]:
            label = self._task_label(task)
            label.setObjectName("monthTaskDone" if task.completed else "monthTask")
            label.setWordWrap(False)
            layout.addWidget(label)
        hidden = max(0, len(courses) - 1) + max(0, len(tasks) - 2)
        if hidden:
            more = QLabel(f"+{hidden} 项")
            more.setObjectName("monthMore")
            layout.addWidget(more)
        layout.addStretch()
        return card

    def _year_card(self, month: int, tasks, courses) -> QWidget:
        card = QFrame()
        is_current = self.anchor.year == date.today().year and month == date.today().month
        card.setObjectName("yearCardCurrent" if is_current else "yearCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)
        heading = QHBoxLayout()
        name = QLabel(f"{month}月")
        name.setObjectName("yearMonth")
        total = len(tasks) + len(courses)
        count = QLabel(f"{total} 项")
        count.setObjectName("yearCount")
        heading.addWidget(name)
        heading.addStretch()
        heading.addWidget(count)
        layout.addLayout(heading)
        remaining = sum(not task.completed for task in tasks)
        details = []
        if remaining:
            details.append(f"{remaining} 项任务")
        if courses:
            details.append(f"{len(courses)} 节课")
        summary = QLabel(" · ".join(details) if details else "暂无安排")
        summary.setObjectName("yearSummary")
        layout.addWidget(summary)
        shown = 0
        if courses:
            course = courses[0]
            label = QLabel(f"{course.name} 等课程")
            label.setObjectName("yearCourse")
            layout.addWidget(label)
            shown = 1
        for task in sorted(tasks, key=lambda item: item.due_at or "9999")[:2 - shown]:
            label = self._task_label(task)
            label.setObjectName("yearTaskDone" if task.completed else "yearTask")
            layout.addWidget(label)
        layout.addStretch()
        return card

    def _task_label(self, task) -> TaskLabel:
        return TaskLabel(
            ("✓ " if task.completed else "• ") + task.title,
            task,
            self.edit_task,
        )

    def _shift_month(self, delta: int) -> date:
        index = self.anchor.year * 12 + self.anchor.month - 1 + delta
        return date(index // 12, index % 12 + 1, 1)

    def _courses(self, day: date):
        if not self.course_service.show_in_calendar:
            return []
        return self.course_service.courses_on(day)

    @staticmethod
    def _course_tooltip(course) -> str:
        details = [course.name, f"{course.start_time}–{course.end_time}"]
        if course.location:
            details.append(course.location)
        if course.teacher:
            details.append(course.teacher)
        return "\n".join(details)

    @staticmethod
    def _date(value: str) -> date:
        try: return datetime.fromisoformat(value).date()
        except ValueError: return date.max
