from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizeGrip, QVBoxLayout

from .theme import rgba
from .widget_base import DesktopWidget


class PomodoroWidget(DesktopWidget, QFrame):
    widget_type = "pomodoro"

    def __init__(self, manager, remaining: int = 1500, end_at: str | None = None, task_id: str | None = None, position: QPoint | None = None, size: tuple[int, int] = (290, 190), always_on_top: bool = False) -> None:
        QFrame.__init__(self); self.init_desktop_widget(manager)
        self.remaining, self.end_at, self.task_id = max(0, remaining), end_at, task_id
        self.running = bool(end_at); self._drag_offset = None
        self.setWindowTitle("番茄钟"); self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True); self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top); self.setMinimumSize(250, 170); self.resize(*size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self); layout.setContentsMargins(18, 15, 18, 15); layout.setSpacing(9)
        heading = QLabel("专注时间"); heading.setObjectName("pomodoroHeading")
        self.time_label = QLabel(); self.time_label.setObjectName("pomodoroValue"); self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tasks = QComboBox(); self.tasks.currentIndexChanged.connect(self._task_changed)
        controls = QHBoxLayout(); self.toggle_button = QPushButton(); self.toggle_button.clicked.connect(self.toggle); reset = QPushButton("重置"); reset.clicked.connect(self.reset); controls.addWidget(self.toggle_button); controls.addWidget(reset)
        layout.addWidget(heading); layout.addWidget(self.time_label); layout.addWidget(self.tasks); layout.addLayout(controls); layout.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        self.apply_theme()
        self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(250)
        manager.plan_service.subscribe(self.refresh_tasks); self.refresh_tasks()
        if position is not None: self.move(position)
        self.tick()
        self.enable_full_context_menu(self._show_context_menu)

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, self.manager.theme.opacity) if self.manager.theme.glass_enabled else theme.accent_soft
        self.setStyleSheet(f"""
            PomodoroWidget {{ background: {background}; border: 1px solid {theme.accent}; border-radius: 15px; }}
            QLabel#pomodoroHeading {{ color: {theme.accent_text}; font-size: 12px; font-weight: 600; }}
            QLabel#pomodoroValue {{ color: {theme.accent_text}; font-size: 36px; font-weight: 700; }}
            QComboBox {{ min-height: 29px; border: 1px solid {theme.accent}; border-radius: 7px; background: white; padding: 0 8px; }}
            QPushButton {{ min-height: 30px; border: none; border-radius: 7px; background: {theme.accent}; color: white; font-weight: 600; }}
            QPushButton:hover {{ background: {theme.accent_hover}; }}
        """)

    def refresh_tasks(self) -> None:
        selected = self.task_id; self.tasks.blockSignals(True); self.tasks.clear(); self.tasks.addItem("不绑定任务", None)
        for item in self.manager.plan_service.items:
            if not item.completed: self.tasks.addItem(f"{item.title} · {item.pomodoros} 次", item.id)
        index = self.tasks.findData(selected); self.tasks.setCurrentIndex(max(0, index)); self.tasks.blockSignals(False)

    def _task_changed(self) -> None:
        self.task_id = self.tasks.currentData(); self.manager.save_state()

    def toggle(self) -> None:
        if self.running:
            self.remaining = self._remaining_from_end(); self.end_at = None; self.running = False
        else:
            if self.remaining <= 0: self.remaining = 1500
            self.end_at = (datetime.now() + timedelta(seconds=self.remaining)).isoformat(); self.running = True
        self.manager.save_state(); self.tick()

    def reset(self) -> None:
        self.remaining, self.end_at, self.running = 1500, None, False; self.manager.save_state(); self.tick()

    def tick(self) -> None:
        remaining = self._remaining_from_end() if self.running else self.remaining
        if self.running and remaining <= 0:
            self.running, self.end_at, self.remaining = False, None, 0
            if self.task_id: self.manager.plan_service.add_pomodoro(self.task_id)
            if self.manager.tray_icon: self.manager.tray_icon.showMessage("专注完成", "一个番茄钟完成了，休息一下吧。")
            self.manager.save_state()
        minutes, seconds = divmod(max(0, remaining), 60); self.time_label.setText(f"{minutes:02d}:{seconds:02d}"); self.toggle_button.setText("暂停" if self.running else ("重新开始" if remaining == 0 else "开始"))

    def _remaining_from_end(self) -> int:
        if not self.end_at: return self.remaining
        try: return max(0, int((datetime.fromisoformat(self.end_at) - datetime.now()).total_seconds()))
        except ValueError: return self.remaining

    def contextMenuEvent(self, event) -> None:
        self._show_context_menu(event.globalPos())
    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self); menu.addAction("打开主界面", self.manager.main_window.show_panel); menu.addSeparator(); top = QAction("窗口置顶", menu, checkable=True); top.setChecked(self.always_on_top); top.triggered.connect(self.set_always_on_top); menu.addAction(top); menu.addSeparator(); menu.addAction("隐藏当前组件", self.hide_to_tray); menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self)); menu.exec(pos)
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 40: self._drag_offset = event.globalPosition().toPoint() - self.pos(); event.accept()
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton: self.move(event.globalPosition().toPoint() - self._drag_offset); event.accept()
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None: self._drag_offset = None; self.manager.save_state()

    def state(self) -> dict[str, Any]:
        return self.common_state() | {"remaining": self._remaining_from_end() if not self.running else self.remaining, "end_at": self.end_at, "task_id": self.task_id, "width": self.width(), "height": self.height()}
