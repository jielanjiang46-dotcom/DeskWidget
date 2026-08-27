from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
    QWidget,
)

from .constants import DEFAULT_IMAGE, IMAGE_FILTER
from .course.service import CourseService
from .countdown_widget import CountdownDialog, CountdownWidget
from .image_widget import ImageWidget
from .main_window import MainWindow
from .note_widget import NoteWidget
from .pomodoro_widget import PomodoroWidget
from .plan.plan_widget import PlanWidget
from .plan.repository import PlanRepository
from .plan.service import PlanService
from .plan.task_dialog import TaskDialog
from .registry import WidgetRegistry
from .state import load_state, save_state
from .theme import ThemeManager
from .widget_base import restored_position
from .window_effects import apply_window_effect
from .week_agenda_widget import WeekAgendaWidget


class WidgetManager:
    """协调主界面、托盘、桌面组件和持久化状态。"""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.widgets: list[QWidget] = []
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        self._tray_hint_shown = False
        self.plan_service = PlanService()
        self.course_service = CourseService()
        self.theme = ThemeManager()
        self.main_window = MainWindow(self)
        self.theme.subscribe(self._theme_changed)
        self.registry = WidgetRegistry()
        self.registry.register("image", self._restore_image)
        self.registry.register("note", self._restore_note)
        self.registry.register("plan", self._restore_plan)
        self.registry.register("pomodoro", self._restore_pomodoro)
        self.registry.register("countdown", self._restore_countdown)
        self.registry.register("week_agenda", self._restore_week_agenda)

    def start(self) -> None:
        self._create_tray_icon()
        restored = self._restore_state()
        if not restored and DEFAULT_IMAGE.exists():
            self.create_image_widget(DEFAULT_IMAGE)
        self.main_window.show_panel()
        self._theme_changed(self.theme.current)

    def _apply_widget_effect(self, widget: QWidget) -> None:
        supports_glass = not isinstance(widget, ImageWidget)
        apply_window_effect(
            widget,
            self.theme.glass_enabled and supports_glass,
            self.theme.opacity,
            self.theme.current.accent_soft,
        )

    def _theme_changed(self, _theme) -> None:
        self.main_window.apply_theme()
        apply_window_effect(self.main_window, False, 100)
        for widget in self.widgets:
            apply_theme = getattr(widget, "apply_theme", None)
            if apply_theme:
                apply_theme()
            supports_glass = not isinstance(widget, ImageWidget)
            apply_window_effect(
                widget,
                self.theme.glass_enabled and supports_glass,
                self.theme.opacity,
                self.theme.current.accent_soft,
            )

    def _create_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray_menu = QMenu()
        self.tray_menu.addAction("打开主界面", self.main_window.show_panel)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("恢复全部组件", self.restore_all)
        self.tray_menu.addAction("隐藏全部组件", self.hide_all)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("退出全部", self.quit_all)

        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("DeskWidget（单击打开主界面）")
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.main_window.show_panel()

    def restore_all(self) -> None:
        for widget in self.widgets:
            widget.show()
            widget.raise_()
            widget.activateWindow()
        self.main_window.refresh_status()

    def hide_all(self) -> None:
        for widget in self.widgets:
            widget.hide()
        self.main_window.refresh_status()
        self.show_tray_hint()

    def show_tray_hint(self) -> None:
        if self.tray_icon is not None and not self._tray_hint_shown:
            self.tray_icon.showMessage(
                "桌面组件已隐藏",
                "单击托盘图标或使用托盘菜单即可恢复。",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            self._tray_hint_shown = True

    def create_image_widget(
        self,
        image_path: Path,
        scale: float | None = None,
        position: QPoint | None = None,
        always_on_top: bool = False,
    ) -> ImageWidget | None:
        try:
            widget = ImageWidget(self, image_path, scale, position, always_on_top)
        except ValueError as error:
            QMessageBox.warning(None, "图片加载失败", str(error))
            return None
        if position is None:
            self._place_new_widget(widget)
        self.widgets.append(widget)
        widget.show()
        self._apply_widget_effect(widget)
        self.main_window.refresh_status()
        self.save_state()
        return widget

    # 保留旧调用名，避免现有扩展或测试立即失效。
    create_widget = create_image_widget

    def create_note(
        self,
        text: str = "",
        color: str = "#fff3b0",
        position: QPoint | None = None,
        size: tuple[int, int] = (260, 220),
        always_on_top: bool = False,
    ) -> NoteWidget:
        note = NoteWidget(self, text, color, position, size, always_on_top)
        if position is None:
            self._place_new_widget(note)
        self.widgets.append(note)
        note.show()
        self._apply_widget_effect(note)
        self.main_window.refresh_status()
        self.save_state()
        return note

    def create_plan_widget(
        self,
        position: QPoint | None = None,
        size: tuple[int, int] = (350, 260),
        always_on_top: bool = False,
    ) -> PlanWidget:
        plan = PlanWidget(self, position, size, always_on_top)
        if position is None:
            self._place_new_widget(plan)
        self.widgets.append(plan)
        plan.show()
        self._apply_widget_effect(plan)
        self.main_window.refresh_status()
        self.save_state()
        return plan

    def create_pomodoro_widget(
        self, remaining: int = 1500, end_at: str | None = None,
        task_id: str | None = None, position: QPoint | None = None,
        size: tuple[int, int] = (290, 190),
        always_on_top: bool = False,
    ) -> PomodoroWidget:
        widget = PomodoroWidget(self, remaining, end_at, task_id, position, size, always_on_top)
        if position is None: self._place_new_widget(widget)
        self.widgets.append(widget); widget.show(); self._apply_widget_effect(widget); self.main_window.refresh_status(); self.save_state()
        return widget

    def create_countdown_widget(
        self, title: str | None = None, target_at: str | None = None,
        mode: str = "countdown", position: QPoint | None = None, always_on_top: bool = False,
        size: tuple[int, int] = (280, 150),
    ) -> CountdownWidget | None:
        if title is None or target_at is None:
            dialog = CountdownDialog(self.main_window)
            if dialog.exec() != dialog.DialogCode.Accepted: return None
            title, target_at, mode = dialog.values()
            if not title: return None
        widget = CountdownWidget(self, title, target_at, mode, position, size, always_on_top)
        if position is None: self._place_new_widget(widget)
        self.widgets.append(widget); widget.show(); self._apply_widget_effect(widget); self.main_window.refresh_status(); self.save_state()
        return widget

    def create_week_agenda_widget(
        self, position: QPoint | None = None,
        size: tuple[int, int] = (800, 460), always_on_top: bool = False,
        anchor: str | None = None,
        collapsed: bool = False, expanded_height: int | None = None,
    ) -> WeekAgendaWidget:
        widget = WeekAgendaWidget(
            self, position, size, always_on_top, anchor, collapsed, expanded_height
        )
        if position is None:
            self._place_new_widget(widget)
        self.widgets.append(widget)
        widget.show()
        self._apply_widget_effect(widget)
        self.main_window.refresh_status()
        self.save_state()
        return widget

    def add_plan_item(self, parent: QWidget | None = None) -> None:
        dialog = TaskDialog(parent or self.main_window)
        if dialog.exec() != TaskDialog.DialogCode.Accepted:
            return
        title, due_at, repeat_weekly = dialog.values()
        if not title:
            QMessageBox.information(dialog, "任务为空", "请输入任务内容。")
            return
        self.plan_service.add(title, due_at, repeat_weekly)

    def add_plan_at(
        self, due_at: datetime, parent: QWidget | None = None
    ) -> None:
        dialog = TaskDialog(parent or self.main_window, initial_due=due_at)
        if dialog.exec() != TaskDialog.DialogCode.Accepted:
            return
        title, due, repeat_weekly = dialog.values()
        if not title:
            QMessageBox.information(dialog, "任务为空", "请输入任务内容。")
            return
        self.plan_service.add(title, due, repeat_weekly)

    def _place_new_widget(self, widget: ImageWidget) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            widget.move(100, 100)
            return
        area = screen.availableGeometry()
        offset = 30 * len(self.widgets)
        widget.move(
            area.center().x() - widget.width() // 2 + offset,
            area.center().y() - widget.height() // 2 + offset,
        )

    def add_from_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self.main_window, "选择要添加的图片", str(Path.home()), IMAGE_FILTER
        )
        if filename:
            self.create_image_widget(Path(filename))

    def change_image(self, widget: ImageWidget) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            widget, "更换图片", str(widget.image_path.parent), IMAGE_FILTER
        )
        if not filename:
            return
        try:
            widget.set_image(Path(filename))
            self.save_state()
        except ValueError as error:
            QMessageBox.warning(widget, "图片加载失败", str(error))

    def duplicate_widget(self, source: ImageWidget) -> None:
        self.create_image_widget(
            source.image_path,
            source._scale,
            source.pos() + QPoint(30, 30),
            source.always_on_top,
        )

    def delete_widget(self, widget: QWidget) -> None:
        answer = QMessageBox.question(
            widget,
            "删除桌面组件",
            "确定删除这个组件吗？\n关联的课程、任务或原始文件不会被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.widgets.remove(widget)
        widget._allow_close = True
        widget.close()
        widget.deleteLater()
        self.main_window.refresh_status()
        self.save_state()

    def save_state(self) -> None:
        save_state({"widgets": [widget.state() for widget in self.widgets]})

    def _restore_state(self) -> bool:
        for item in load_state().get("widgets", []):
            if not isinstance(item, dict):
                continue
            widget_type = str(item.get("type") or ("image" if "image" in item else ""))
            self.registry.create(widget_type, item)
        return bool(self.widgets)

    def _restore_image(self, item: dict) -> ImageWidget | None:
        image_path = Path(item.get("image", ""))
        if not image_path.is_file():
            return None
        return self.create_image_widget(
            image_path,
            float(item.get("scale", 1.0)),
            restored_position(item),
            bool(item.get("always_on_top", False)),
        )

    def _restore_note(self, item: dict) -> NoteWidget:
        return self.create_note(
            str(item.get("text", "")),
            str(item.get("color", "#fff3b0")),
            restored_position(item),
            (int(item.get("width", 260)), int(item.get("height", 220))),
            bool(item.get("always_on_top", False)),
        )

    def _restore_plan(self, item: dict) -> PlanWidget:
        return self.create_plan_widget(
            restored_position(item),
            (int(item.get("width", 350)), int(item.get("height", 260))),
            bool(item.get("always_on_top", False)),
        )

    def _restore_pomodoro(self, item: dict) -> PomodoroWidget:
        return self.create_pomodoro_widget(
            int(item.get("remaining", 1500)), item.get("end_at"), item.get("task_id"),
            restored_position(item),
            (int(item.get("width", 290)), int(item.get("height", 190))),
            bool(item.get("always_on_top", False)),
        )

    def _restore_countdown(self, item: dict) -> CountdownWidget | None:
        title, target = str(item.get("title", "倒数日")), str(item.get("target_at", ""))
        if not target: return None
        return self.create_countdown_widget(
            title, target, str(item.get("mode", "countdown")), restored_position(item),
            bool(item.get("always_on_top", False)),
            (int(item.get("width", 280)), int(item.get("height", 150))),
        )

    def _restore_week_agenda(self, item: dict) -> WeekAgendaWidget:
        return self.create_week_agenda_widget(
            restored_position(item),
            (int(item.get("width", 800)), int(item.get("height", 460))),
            bool(item.get("always_on_top", False)),
            str(item.get("anchor", "")) or None,
            bool(item.get("collapsed", False)),
            int(item.get("expanded_height", 460)),
        )

    def quit_all(self) -> None:
        self.save_state()
        for widget in self.widgets:
            widget._allow_close = True
            widget.close()
        self.main_window._allow_close = True
        self.main_window.close()
        self.app.quit()
