from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox, QDateTimeEdit, QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)


class TaskDialog(QDialog):
    def __init__(self, parent=None, item=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑任务" if item else "新建计划")
        self.setMinimumWidth(340)
        layout = QFormLayout(self)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("要完成什么？")
        self.use_due = QCheckBox("设置截止时间")
        self.due_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.due_edit.setEnabled(False)
        self.use_due.toggled.connect(self.due_edit.setEnabled)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow("任务", self.title_edit)
        layout.addRow(self.use_due)
        layout.addRow("截止", self.due_edit)
        layout.addRow(buttons)
        if item is not None:
            self.title_edit.setText(item.title)
            if item.due_at:
                self.use_due.setChecked(True)
                self.due_edit.setDateTime(QDateTime.fromString(item.due_at, Qt.DateFormat.ISODate))

    def values(self) -> tuple[str, str | None]:
        due = self.due_edit.dateTime().toPython().isoformat() if self.use_due.isChecked() else None
        return self.title_edit.text().strip(), due
