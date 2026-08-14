from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from .plan.plan_center import PlanCenter
from .productivity_views import CountdownPage, PomodoroPage
from .settings_window import SettingsWindow

if TYPE_CHECKING:
    from .manager import WidgetManager


class MainWindow(QMainWindow):
    """DeskWidget 紧凑工作台。"""

    def __init__(self, manager: "WidgetManager") -> None:
        super().__init__()
        self.manager = manager
        self._allow_close = False
        self.setWindowTitle("DeskWidget")
        self.resize(840, 620)
        self.setMinimumSize(720, 540)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(28, 20, 28, 24)
        root.setSpacing(18)
        root.addLayout(self._build_header())

        self.pages = QStackedWidget()
        self.widget_page = self._build_widget_page()
        self.plan_center = PlanCenter(manager)
        self.pages.addWidget(self.widget_page)
        self.pages.addWidget(self.plan_center)
        self.pomodoro_page = PomodoroPage(manager)
        self.countdown_page = CountdownPage(manager)
        self.pages.addWidget(self.pomodoro_page)
        self.pages.addWidget(self.countdown_page)
        root.addWidget(self.pages, 1)
        self.setCentralWidget(container)
        self._apply_style()
        self.refresh_status()

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(18)
        brand = QLabel("DeskWidget")
        brand.setObjectName("brand")
        header.addWidget(brand)
        header.addSpacing(14)
        self.tabs = QButtonGroup(self)
        self.tabs.setExclusive(True)
        for index, text in enumerate(("组件", "任务", "日历", "番茄钟", "倒数日")):
            button = QPushButton(text)
            button.setObjectName("topTab")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, page=index: self.switch_page(page))
            self.tabs.addButton(button)
            header.addWidget(button)
            if index == 0:
                button.setChecked(True)
        header.addStretch()
        self.header_status = QLabel()
        self.header_status.setObjectName("headerStatus")
        header.addWidget(self.header_status)
        settings = QPushButton("设置")
        settings.setObjectName("settingsButton")
        settings.clicked.connect(self.open_settings)
        header.addWidget(settings)
        return header

    def open_settings(self) -> None:
        SettingsWindow(self.manager).exec()

    def switch_page(self, page: int) -> None:
        if page == 0:
            self.pages.setCurrentIndex(0)
        elif page in (1, 2):
            self.pages.setCurrentIndex(1)
            if page == 1:
                self.plan_center.show_tasks()
            else:
                self.plan_center.show_calendar()
        elif page == 3:
            self.pages.setCurrentIndex(2)
            self.pomodoro_page.refresh()
        else:
            self.pages.setCurrentIndex(3)
            self.countdown_page.refresh()

    def _build_widget_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        title = QLabel("桌面组件")
        title.setObjectName("pageTitle")
        subtitle = QLabel("选择一个组件添加到桌面，随时可以从托盘恢复")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        cards.addWidget(self._card("图片", "展示课表、日程或参考图片", "选择图片", self.manager.add_from_dialog), 0, 0)
        cards.addWidget(self._card("便签", "快速记录想法，内容自动保存", "新建便签", self.manager.create_note), 0, 1)
        cards.addWidget(self._card("今日计划", "在桌面查看任务和剩余时间", "添加计划", self.manager.create_plan_widget), 0, 2)
        cards.addWidget(self._card("番茄钟", "可绑定任务，隐藏后继续准确计时", "添加番茄钟", self.manager.create_pomodoro_widget), 1, 0)
        cards.addWidget(self._card("倒数日与纪念日", "记录未来期待，也纪念已经发生的重要日子", "新建事件", self.manager.create_countdown_widget), 1, 1)
        layout.addLayout(cards)
        layout.addStretch()
        footer = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        show = QPushButton("显示全部")
        hide = QPushButton("隐藏全部")
        show.setObjectName("footerAction")
        hide.setObjectName("footerAction")
        show.clicked.connect(self.manager.restore_all)
        hide.clicked.connect(self.manager.hide_all)
        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(show)
        footer.addWidget(hide)
        layout.addLayout(footer)
        scroll.setWidget(page)
        return scroll

    def _card(self, title: str, description: str, action: str, callback) -> QWidget:
        card = QFrame()
        card.setObjectName("componentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 16)
        name = QLabel(title)
        name.setObjectName("cardTitle")
        detail = QLabel(description)
        detail.setObjectName("cardDescription")
        detail.setWordWrap(True)
        button = QPushButton(action)
        button.setObjectName("primary")
        button.clicked.connect(lambda _checked=False: callback())
        layout.addWidget(name)
        layout.addWidget(detail)
        layout.addStretch()
        layout.addWidget(button)
        return card

    def _apply_style(self) -> None:
        self.apply_theme()

    def apply_theme(self) -> None:
        theme = self.manager.theme.current
        style = """
            QMainWindow, QWidget { background: #F8F9FC; color: #252A34; font-family: "Microsoft YaHei UI"; }
            QLabel#brand {{ font-size: 18px; font-weight: 700; color: {theme.accent_text}; }}
            QLabel#headerStatus, QLabel#status, QLabel#planSummary { color: #8A919E; font-size: 11px; }
            QPushButton#topTab { min-width: 54px; min-height: 34px; border: none; border-radius: 8px; background: transparent; color: #737B89; font-weight: 600; }
            QPushButton#topTab:hover { background: #EFF1F6; }
            QPushButton#topTab:checked {{ background: {theme.accent_soft}; color: {theme.accent_text}; }}
            QPushButton#settingsButton {{ min-width: 48px; min-height: 32px; border: 1px solid #E0E3E9; border-radius: 8px; background: white; color: #555D69; }}
            QPushButton#settingsButton:hover {{ border-color: {theme.accent}; color: {theme.accent_text}; }}
            QLabel#pageTitle { font-size: 23px; font-weight: 700; color: #20242D; }
            QLabel#subtitle { color: #8B929E; font-size: 12px; }
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QFrame#componentCard { background: white; border: 1px solid #E7E9EE; border-radius: 13px; min-height: 132px; max-height: 150px; }
            QLabel#cardTitle { font-size: 16px; font-weight: 700; }
            QLabel#cardDescription { color: #858C98; font-size: 11px; }
            QPushButton { min-height: 34px; border: 1px solid #E0E3E9; border-radius: 8px; background: white; color: #4C5360; padding: 0 12px; }
            QPushButton:hover { background: #F0F2F6; }
            QPushButton#primary {{ border: none; background: {theme.accent}; color: white; font-weight: 600; }}
            QPushButton#primary:hover {{ background: {theme.accent_hover}; }}
            QPushButton#filterChip { min-height: 29px; border: none; background: #F0F2F6; color: #737B87; }
            QPushButton#filterChip:checked {{ background: {theme.accent_soft}; color: {theme.accent_text}; font-weight: 600; }}
            QFrame#quickAdd { background: white; border: 1px solid #E4E7ED; border-radius: 10px; }
            QFrame#quickAdd QLineEdit { border: none; background: transparent; min-height: 33px; }
            QListWidget { border: none; background: transparent; outline: none; }
            QListWidget::item { border: none; }
            PlanTaskRow { background: white; border: 1px solid #ECEEF2; border-radius: 9px; }
            QLabel#taskTitle { font-size: 13px; font-weight: 500; }
            QLabel#completedTask { color: #A1A7B0; text-decoration: line-through; }
            QLabel#due { color: #818997; font-size: 10px; }
            QLabel#overdue { color: #D86A52; font-size: 10px; font-weight: 600; }
            QFrame#toolCard { background: white; border: 1px solid #E7E9EF; border-radius: 9px; }
            QLabel#toolTitle { color: #858C98; font-size: 10px; font-weight: 600; }
            QLabel#countdown { color: #343A46; font-size: 12px; font-weight: 600; }
            QLabel#pomodoroTime {{ color: {theme.accent_text}; font-size: 17px; font-weight: 700; }}
            QComboBox { min-height: 31px; border: 1px solid #E1E4EA; border-radius: 7px; background: #FAFBFD; padding: 0 8px; }
            QTableWidget { background: white; border: 1px solid #E7E9EE; border-radius: 9px; gridline-color: #ECEEF2; }
            QHeaderView::section { background: #F4F5F8; color: #737B87; border: none; padding: 7px; font-weight: 600; }
            QFrame#weekCard, QFrame#weekCardToday { background: white; border: none; }
            QFrame#weekCardToday {{ background: {theme.accent_soft}; border-radius: 10px; }}
            QLabel#weekDay { color: #7F8794; font-size: 11px; font-weight: 600; }
            QLabel#weekNumber { color: #252A34; font-size: 22px; font-weight: 700; }
            QLabel#weekTask {{ background: {theme.accent_soft}; color: {theme.accent_text}; border-radius: 6px; padding: 5px 7px; font-size: 11px; }}
            QLabel#weekTaskDone { background: #F0F1F3; color: #9AA0AA; border-radius: 6px; padding: 5px 7px; text-decoration: line-through; }
            QLabel#weekEmpty { color: #B0B5BE; font-size: 10px; }
            QFrame#monthCard, QFrame#monthCardToday, QFrame#monthCardMuted { background: white; border: none; }
            QFrame#monthCardToday {{ background: {theme.accent_soft}; border-radius: 9px; }}
            QFrame#monthCardMuted { background: #FAFAFB; }
            QLabel#monthNumber { color: #343A45; font-size: 13px; font-weight: 700; }
            QLabel#monthNumberMuted { color: #C1C5CC; font-size: 13px; }
            QLabel#monthTask {{ background: {theme.accent_soft}; color: {theme.accent_text}; border-radius: 5px; padding: 3px 5px; font-size: 10px; }}
            QLabel#monthTaskDone { background: #F0F1F3; color: #A0A5AD; border-radius: 5px; padding: 3px 5px; text-decoration: line-through; font-size: 10px; }
            QLabel#monthMore { color: #9198A4; font-size: 9px; }
            QFrame#yearCard, QFrame#yearCardCurrent { background: white; border: none; }
            QFrame#yearCardCurrent {{ background: {theme.accent_soft}; border-radius: 11px; }}
            QLabel#yearMonth { color: #292F39; font-size: 18px; font-weight: 700; }
            QLabel#yearCount {{ background: {theme.accent_soft}; color: {theme.accent_text}; border-radius: 7px; padding: 3px 7px; font-size: 10px; }}
            QLabel#yearSummary { color: #9299A4; font-size: 10px; }
            QLabel#yearTask {{ color: {theme.accent_text}; font-size: 10px; font-weight: 600; }}
            QLabel#yearTaskDone { color: #A0A5AD; font-size: 10px; text-decoration: line-through; }
        """
        for token, value in {
            "{theme.accent}": theme.accent,
            "{theme.accent_hover}": theme.accent_hover,
            "{theme.accent_soft}": theme.accent_soft,
            "{theme.accent_text}": theme.accent_text,
        }.items():
            style = style.replace(token, value)
        self.setStyleSheet(style.replace("{{", "{").replace("}}", "}"))

    def refresh_status(self) -> None:
        visible = sum(widget.isVisible() for widget in self.manager.widgets)
        total = len(self.manager.widgets)
        self.status_label.setText(f"{total} 个组件，其中 {visible} 个正在显示")
        self.header_status.setText(f"{total} 个组件")

    def show_panel(self) -> None:
        self.refresh_status()
        self.plan_center.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
            self.hide()
