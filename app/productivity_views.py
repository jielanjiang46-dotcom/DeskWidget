from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from .countdown_widget import CountdownWidget
from .pomodoro_widget import PomodoroWidget


class PomodoroPage(QWidget):
    def __init__(self, manager) -> None:
        super().__init__(); self.manager = manager
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 8, 0, 0); layout.setSpacing(14)
        header = QHBoxLayout(); title = QLabel("番茄钟"); title.setObjectName("pageTitle")
        add = QPushButton("＋ 新建番茄钟"); add.setObjectName("primary"); add.clicked.connect(lambda: manager.create_pomodoro_widget())
        header.addWidget(title); header.addStretch(); header.addWidget(add); layout.addLayout(header)
        subtitle = QLabel("所有计时都来自桌面番茄钟，隐藏后仍会继续运行")
        subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["绑定任务", "剩余时间", "状态", "操作"])
        self.table.horizontalHeader().setStretchLastSection(True); self.table.verticalHeader().hide(); layout.addWidget(self.table)
        self._widget_ids = []
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(500); self.refresh()

    def refresh(self) -> None:
        widgets = [x for x in self.manager.widgets if isinstance(x, PomodoroWidget)]
        ids = [id(x) for x in widgets]
        rebuild = ids != self._widget_ids
        if rebuild:
            self._widget_ids = ids; self.table.setRowCount(len(widgets))
        for row, widget in enumerate(widgets):
            task = next((x.title for x in self.manager.plan_service.items if x.id == widget.task_id), "未绑定任务")
            remaining = widget._remaining_from_end() if widget.running else widget.remaining
            minutes, seconds = divmod(max(0, remaining), 60)
            self.table.setItem(row, 0, QTableWidgetItem(task)); self.table.setItem(row, 1, QTableWidgetItem(f"{minutes:02d}:{seconds:02d}")); self.table.setItem(row, 2, QTableWidgetItem("专注中" if widget.running else "已暂停"))
            if rebuild:
                controls = QWidget(); actions = QHBoxLayout(controls); actions.setContentsMargins(0, 2, 0, 2)
                toggle = QPushButton("开始"); toggle.clicked.connect(widget.toggle); toggle.setProperty("toggle", True)
                reset = QPushButton("重置"); reset.clicked.connect(widget.reset)
                show = QPushButton("显示到桌面"); show.clicked.connect(lambda _checked=False, value=widget: self._show(value))
                actions.addWidget(toggle); actions.addWidget(reset); actions.addWidget(show); self.table.setCellWidget(row, 3, controls)
            toggle = next((x for x in self.table.cellWidget(row, 3).findChildren(QPushButton) if x.property("toggle")), None)
            if toggle: toggle.setText("暂停" if widget.running else "开始")

    @staticmethod
    def _show(widget) -> None:
        widget.show(); widget.raise_(); widget.activateWindow()


class CountdownPage(QWidget):
    def __init__(self, manager) -> None:
        super().__init__(); self.manager = manager
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 8, 0, 0); layout.setSpacing(14)
        header = QHBoxLayout(); title = QLabel("倒数日"); title.setObjectName("pageTitle")
        add = QPushButton("＋ 新建事件"); add.setObjectName("primary"); add.clicked.connect(lambda: manager.create_countdown_widget())
        header.addWidget(title); header.addStretch(); header.addWidget(add); layout.addLayout(header)
        subtitle = QLabel("统一管理倒数日和纪念日，每个事件都可以显示为桌面组件")
        subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["类型", "事件", "计时", "日期", "操作"])
        self.table.horizontalHeader().setStretchLastSection(True); self.table.verticalHeader().hide(); layout.addWidget(self.table)
        self._widget_ids = []
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.refresh()

    def refresh(self) -> None:
        widgets = [x for x in self.manager.widgets if isinstance(x, CountdownWidget)]
        ids = [id(x) for x in widgets]
        rebuild = ids != self._widget_ids
        if rebuild:
            self._widget_ids = ids; self.table.setRowCount(len(widgets))
        for row, widget in enumerate(widgets):
            kind = "纪念日" if widget.mode == "anniversary" else "倒数日"
            self.table.setItem(row, 0, QTableWidgetItem(kind)); self.table.setItem(row, 1, QTableWidgetItem(widget.title_text)); self.table.setItem(row, 2, QTableWidgetItem(widget.value_label.text())); self.table.setItem(row, 3, QTableWidgetItem(widget.detail_label.text().split("·")[-1].strip()))
            if rebuild:
                controls = QWidget(); actions = QHBoxLayout(controls); actions.setContentsMargins(0, 2, 0, 2)
                edit = QPushButton("编辑"); edit.clicked.connect(widget.edit)
                show = QPushButton("显示到桌面"); show.clicked.connect(lambda _checked=False, value=widget: self._show(value))
                actions.addWidget(edit); actions.addWidget(show); self.table.setCellWidget(row, 4, controls)

    @staticmethod
    def _show(widget) -> None:
        widget.show(); widget.raise_(); widget.activateWindow()
