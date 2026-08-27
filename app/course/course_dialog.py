from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QMessageBox, QTimeEdit,
)


class CourseDialog(QDialog):
    """Create or edit one weekly course slot."""

    def __init__(self, parent=None, course=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑课程" if course else "新建课程")
        self.setMinimumWidth(430)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(course.name if course else "")
        self.name_edit.setPlaceholderText("例如：COMP2011 LEC001")
        self.weekday_edit = QComboBox()
        self.weekday_edit.addItems(
            ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        )
        self.weekday_edit.setCurrentIndex(course.weekday if course else 0)
        self.start_edit = QTimeEdit()
        self.end_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.end_edit.setDisplayFormat("HH:mm")
        self.start_edit.setTime(QTime.fromString(course.start_time, "HH:mm") if course else QTime(8, 0))
        self.end_edit.setTime(QTime.fromString(course.end_time, "HH:mm") if course else QTime(9, 0))
        self.location_edit = QLineEdit(course.location if course else "")
        self.teacher_edit = QLineEdit(course.teacher if course else "")
        self.limit_dates = QCheckBox("限制课程日期范围")
        has_dates = bool(course and (course.start_date or course.end_date))
        self.limit_dates.setChecked(has_dates)
        self.start_date_edit = QDateEdit()
        self.end_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        today = QDate.currentDate()
        self.start_date_edit.setDate(
            QDate.fromString(course.start_date, "yyyy-MM-dd") if course and course.start_date else today
        )
        self.end_date_edit.setDate(
            QDate.fromString(course.end_date, "yyyy-MM-dd") if course and course.end_date else today.addMonths(4)
        )
        self.limit_dates.toggled.connect(self.start_date_edit.setEnabled)
        self.limit_dates.toggled.connect(self.end_date_edit.setEnabled)
        self.start_date_edit.setEnabled(has_dates)
        self.end_date_edit.setEnabled(has_dates)

        layout.addRow("课程名称", self.name_edit)
        layout.addRow("星期", self.weekday_edit)
        layout.addRow("开始时间", self.start_edit)
        layout.addRow("结束时间", self.end_edit)
        layout.addRow("地点", self.location_edit)
        layout.addRow("教师", self.teacher_edit)
        layout.addRow(self.limit_dates)
        layout.addRow("开始日期", self.start_date_edit)
        layout.addRow("结束日期", self.end_date_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _accept_if_valid(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.information(self, "课程名称为空", "请输入课程名称。")
            return
        if self.start_edit.time() >= self.end_edit.time():
            QMessageBox.information(self, "时间范围无效", "结束时间必须晚于开始时间。")
            return
        if self.limit_dates.isChecked() and self.start_date_edit.date() > self.end_date_edit.date():
            QMessageBox.information(self, "日期范围无效", "结束日期不能早于开始日期。")
            return
        self.accept()

    def values(self) -> tuple[str, int, str, str, str, str, str, str]:
        limited = self.limit_dates.isChecked()
        return (
            self.name_edit.text().strip(), self.weekday_edit.currentIndex(),
            self.start_edit.time().toString("HH:mm"),
            self.end_edit.time().toString("HH:mm"),
            self.location_edit.text().strip(), self.teacher_edit.text().strip(),
            self.start_date_edit.date().toString("yyyy-MM-dd") if limited else "",
            self.end_date_edit.date().toString("yyyy-MM-dd") if limited else "",
        )
