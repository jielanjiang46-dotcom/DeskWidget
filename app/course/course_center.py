from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .course_dialog import CourseDialog


class CourseCenter(QWidget):
    """Import and manage the recurring weekly course schedule."""

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("课表")
        title.setObjectName("pageTitle")
        hint = QLabel("导入 ICS 或 CSV 课表后，会自动按星期显示；可在日历中控制是否叠加课程。")
        hint.setObjectName("subtitle")
        title_group.addWidget(title)
        title_group.addWidget(hint)
        heading.addLayout(title_group)
        heading.addStretch()
        sample = QPushButton("导入格式说明")
        sample.clicked.connect(self.show_import_help)
        import_button = QPushButton("导入课表")
        import_button.setObjectName("primary")
        import_button.clicked.connect(self.import_schedule)
        add_button = QPushButton("新建课程")
        add_button.clicked.connect(self.add_course)
        heading.addWidget(sample)
        heading.addWidget(add_button)
        heading.addWidget(import_button)
        layout.addLayout(heading)

        self.summary = QLabel()
        self.summary.setObjectName("planSummary")
        layout.addWidget(self.summary)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["星期", "课程", "时间", "地点", "教师", "开始日期", "结束日期", "操作"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(
            lambda row, _column: self.edit_course(self._row_courses[row])
            if 0 <= row < len(self._row_courses) else None
        )
        layout.addWidget(self.table, 1)
        footer = QHBoxLayout()
        footer.addStretch()
        clear = QPushButton("清空课表")
        clear.clicked.connect(self.clear_courses)
        footer.addWidget(clear)
        layout.addLayout(footer)
        manager.course_service.subscribe(self.refresh)
        self._row_courses = []
        self.refresh()

    def add_course(self) -> None:
        dialog = CourseDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.manager.course_service.add(*dialog.values())

    def edit_course(self, course) -> None:
        dialog = CourseDialog(self, course)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.manager.course_service.update(course.id, *dialog.values())

    def import_schedule(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择课表文件", str(Path.home()),
            "课表文件 (*.ics *.csv);;iCalendar 文件 (*.ics);;CSV 文件 (*.csv)"
        )
        if not filename:
            return
        try:
            count, errors = self.manager.course_service.import_file(Path(filename))
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "导入失败", str(error))
            return
        message = f"成功导入 {count} 个课程时段。"
        if errors:
            preview = "\n".join(errors[:8])
            suffix = f"\n另有 {len(errors) - 8} 条错误。" if len(errors) > 8 else ""
            message += f"\n\n未导入的行：\n{preview}{suffix}"
        QMessageBox.information(self, "课表导入完成", message)

    def show_import_help(self) -> None:
        QMessageBox.information(
            self, "课表导入格式说明",
            "可直接导入学校或日历软件导出的 .ics 文件。\n\n"
            "CSV 必填列：课程、星期、开始时间、结束时间\n"
            "可选列：地点、教师、开始日期、结束日期\n\n"
            "示例：\n"
            "课程,星期,开始时间,结束时间,地点,教师,开始日期,结束日期\n"
            "高等数学,周一,08:00,09:40,A101,张老师,2026-09-01,2027-01-15\n\n"
            "星期也可以填写 1—7，日期使用 YYYY-MM-DD。",
        )

    def clear_courses(self) -> None:
        if not self.manager.course_service.items:
            return
        answer = QMessageBox.question(
            self, "清空课表", "确定删除全部课程吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.course_service.clear()

    def refresh(self) -> None:
        weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        items = sorted(
            self.manager.course_service.items,
            key=lambda item: (item.weekday, item.start_time, item.name),
        )
        self._row_courses = items
        self.summary.setText(f"共 {len(items)} 节课程")
        self.table.setRowCount(len(items))
        for row, course in enumerate(items):
            values = (
                weekdays[course.weekday], course.name,
                f"{course.start_time}–{course.end_time}", course.location,
                course.teacher,
                self._date_text(course, True), self._date_text(course, False),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row, column, item)
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(2)
            edit = QPushButton("编辑")
            edit.setObjectName("taskEdit")
            edit.clicked.connect(
                lambda _checked=False, value=course: self.edit_course(value)
            )
            delete = QPushButton("删除")
            delete.setObjectName("taskEdit")
            delete.clicked.connect(
                lambda _checked=False, item_id=course.id:
                self.manager.course_service.delete(item_id)
            )
            action_layout.addWidget(edit)
            action_layout.addWidget(delete)
            self.table.setCellWidget(row, 7, actions)
        self.table.resizeColumnsToContents()

    @staticmethod
    def _date_text(course, first: bool) -> str:
        value = course.start_date if first else course.end_date
        if not value:
            return "不限"
        if course.dates and not first:
            return f"{value}（共 {len(course.dates)} 次）"
        return value
