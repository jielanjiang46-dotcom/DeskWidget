from datetime import datetime
from typing import Any

from PySide6.QtCore import QDateTime, QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox, QFormLayout, QFrame, QLabel, QLineEdit, QMenu, QSizeGrip, QVBoxLayout

from .theme import rgba
from .widget_base import DesktopWidget


class CountdownDialog(QDialog):
    def __init__(self, parent=None, title: str = "", target_at: str | None = None, mode: str = "countdown") -> None:
        super().__init__(parent)
        self.setWindowTitle("设置倒数日")
        layout = QFormLayout(self)
        self.mode_edit = QComboBox()
        self.mode_edit.addItem("倒数日", "countdown")
        self.mode_edit.addItem("纪念日", "anniversary")
        mode_index = self.mode_edit.findData(mode)
        self.mode_edit.setCurrentIndex(max(0, mode_index))
        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("例如：毕业典礼")
        self.target_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.target_edit.setCalendarPopup(True)
        self.target_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.mode_edit.currentIndexChanged.connect(self._update_labels)
        if target_at:
            value = QDateTime.fromString(target_at, Qt.DateFormat.ISODate)
            if value.isValid(): self.target_edit.setDateTime(value)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addRow("模式", self.mode_edit)
        layout.addRow("事件", self.title_edit)
        self.date_label = QLabel()
        layout.addRow(self.date_label, self.target_edit)
        layout.addRow(buttons)
        self._update_labels()

    def _update_labels(self) -> None:
        anniversary = self.mode_edit.currentData() == "anniversary"
        self.date_label.setText("纪念日期" if anniversary else "目标时间")
        self.setWindowTitle("设置纪念日" if anniversary else "设置倒数日")

    def values(self) -> tuple[str, str, str]:
        return (
            self.title_edit.text().strip(),
            self.target_edit.dateTime().toPython().isoformat(),
            str(self.mode_edit.currentData()),
        )


class CountdownWidget(DesktopWidget, QFrame):
    widget_type = "countdown"

    def __init__(self, manager, title: str, target_at: str, mode: str = "countdown", position: QPoint | None = None, size: tuple[int, int] = (280, 150), always_on_top: bool = False) -> None:
        QFrame.__init__(self); self.init_desktop_widget(manager)
        self.title_text, self.target_at = title, target_at
        self.mode = mode if mode in ("countdown", "anniversary") else "countdown"
        self._drag_offset = None
        self.setWindowTitle("倒数日")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(230, 135); self.resize(*size)
        layout = QVBoxLayout(self); layout.setContentsMargins(18, 16, 18, 16)
        self.title_label = QLabel(); self.title_label.setObjectName("countdownTitle")
        self.value_label = QLabel(); self.value_label.setObjectName("countdownValue")
        self.value_label.setWordWrap(True)
        self.detail_label = QLabel(); self.detail_label.setObjectName("countdownDetail")
        layout.addWidget(self.title_label); layout.addStretch(); layout.addWidget(self.value_label); layout.addWidget(self.detail_label); layout.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        self.apply_theme()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000)
        if position is not None: self.move(position)
        self.refresh()
        self.enable_full_context_menu(self._show_context_menu)

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        background = rgba(theme.accent_soft, self.manager.theme.opacity) if self.manager.theme.glass_enabled else theme.accent_soft
        self.setStyleSheet(f"""
            CountdownWidget {{ background: {background}; border: 1px solid {theme.accent}; border-radius: 15px; }}
            QLabel#countdownTitle {{ color: {theme.accent_text}; font-size: 18px; font-weight: 700; }}
            QLabel#countdownValue {{ color: {theme.accent}; font-size: 29px; font-weight: 700; }}
            QLabel#countdownDetail {{ color: {theme.accent_text}; font-size: 10px; }}
        """)

    def refresh(self) -> None:
        try: target = datetime.fromisoformat(self.target_at)
        except ValueError: target = datetime.now()
        now = datetime.now()
        raw_seconds = int((target - now).total_seconds())
        seconds = abs(raw_seconds)
        days, rem = divmod(seconds, 86400); hours, rem = divmod(rem, 3600); minutes, secs = divmod(rem, 60)
        if self.mode == "anniversary":
            self.title_label.setText("纪念日")
            if raw_seconds <= 0:
                self.value_label.setText(f"{self.title_text} 已经 {days} 天")
            else:
                self.value_label.setText(f"距离 {self.title_text} 还有 {days} 天")
        else:
            self.title_label.setText("倒数日")
            if raw_seconds >= 0:
                self.value_label.setText(f"距离 {self.title_text} 还有 {days} 天")
            else:
                self.value_label.setText(f"{self.title_text} 已经过去 {days} 天")
        self.detail_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}  ·  {target:%Y年%m月%d日 %H:%M}")

    def edit(self) -> None:
        dialog = CountdownDialog(self, self.title_text, self.target_at, self.mode)
        if dialog.exec() == dialog.DialogCode.Accepted:
            title, target, mode = dialog.values()
            if title:
                self.title_text, self.target_at, self.mode = title, target, mode
                self.refresh(); self.manager.save_state()

    def contextMenuEvent(self, event) -> None:
        self._show_context_menu(event.globalPos())
    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self); menu.addAction("打开主界面", self.manager.main_window.show_panel); menu.addSeparator(); menu.addAction("编辑事件…", self.edit)
        top = QAction("窗口置顶", menu, checkable=True); top.setChecked(self.always_on_top); top.triggered.connect(self.set_always_on_top); menu.addAction(top)
        menu.addSeparator(); menu.addAction("隐藏当前组件", self.hide_to_tray); menu.addAction("删除这个组件", lambda: self.manager.delete_widget(self)); menu.exec(pos)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos(); event.accept()
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset); event.accept()
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None: self._drag_offset = None; self.manager.save_state()

    def state(self) -> dict[str, Any]:
        return self.common_state() | {"title": self.title_text, "target_at": self.target_at, "mode": self.mode, "width": self.width(), "height": self.height()}
