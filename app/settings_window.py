from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from .theme import THEMES


class SettingsWindow(QDialog):
    def __init__(self, manager) -> None:
        super().__init__(manager.main_window)
        self.manager = manager
        self.setWindowTitle("设置")
        self.setFixedSize(520, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 24)
        title = QLabel("设置"); title.setObjectName("settingsTitle")
        section = QLabel("个性化"); section.setObjectName("settingsSection")
        hint = QLabel("主题颜色会应用到主界面和桌面组件。")
        hint.setObjectName("settingsHint")
        layout.addWidget(title); layout.addSpacing(12); layout.addWidget(section); layout.addWidget(hint); layout.addSpacing(12)
        colors = QHBoxLayout(); colors.setSpacing(12)
        self.buttons = QButtonGroup(self); self.buttons.setExclusive(True)
        for key, theme in THEMES.items():
            button = QPushButton(theme.name)
            button.setCheckable(True); button.setProperty("themeKey", key)
            button.setFixedSize(64, 72)
            button.setStyleSheet(f"""
                QPushButton {{ background: {theme.accent}; color: white; border: 3px solid transparent; border-radius: 12px; font-weight: 600; }}
                QPushButton:hover {{ background: {theme.accent_hover}; }}
                QPushButton:checked {{ border-color: #252A34; }}
            """)
            button.clicked.connect(lambda _checked=False, value=key: self._select_theme(value))
            button.setChecked(key == manager.theme.current_key)
            self.buttons.addButton(button); colors.addWidget(button)
        layout.addLayout(colors)
        layout.addSpacing(20)
        glass_title = QLabel("窗口效果"); glass_title.setObjectName("settingsSection")
        self.glass_check = QCheckBox("开启半透明毛玻璃效果")
        self.glass_check.setChecked(manager.theme.glass_enabled)
        self.glass_check.toggled.connect(manager.theme.set_glass)
        self.glass_check.toggled.connect(lambda _enabled: self._update_preview())
        opacity_row = QHBoxLayout()
        opacity_text = QLabel("背景透明度")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(40, 100)
        self.opacity_slider.setValue(manager.theme.opacity)
        self.opacity_value = QLabel(f"{manager.theme.opacity}%")
        self.opacity_value.setFixedWidth(42)
        self.opacity_slider.valueChanged.connect(self._opacity_changed)
        self.opacity_slider.setEnabled(manager.theme.glass_enabled)
        self.glass_check.toggled.connect(self.opacity_slider.setEnabled)
        opacity_row.addWidget(opacity_text); opacity_row.addWidget(self.opacity_slider, 1); opacity_row.addWidget(self.opacity_value)
        self.preview = QFrame()
        self.preview.setObjectName("glassPreview")
        preview_layout = QHBoxLayout(self.preview)
        preview_layout.setContentsMargins(14, 10, 14, 10)
        preview_title = QLabel("文字始终清晰")
        preview_title.setObjectName("previewTitle")
        self.preview_hint = QLabel()
        self.preview_hint.setObjectName("previewHint")
        preview_layout.addWidget(preview_title)
        preview_layout.addStretch()
        preview_layout.addWidget(self.preview_hint)
        layout.addWidget(glass_title); layout.addWidget(self.glass_check); layout.addLayout(opacity_row); layout.addWidget(self.preview); layout.addStretch()
        close = QPushButton("完成"); close.setObjectName("settingsDone"); close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.setStyleSheet("""
            QDialog { background: #F8F9FC; color: #252A34; font-family: "Microsoft YaHei UI"; }
            QLabel#settingsTitle { font-size: 22px; font-weight: 700; }
            QLabel#settingsSection { font-size: 15px; font-weight: 700; }
            QLabel#settingsHint { color: #838A97; font-size: 11px; }
            QPushButton#settingsDone { min-width: 80px; min-height: 32px; border: 1px solid #DDE0E6; border-radius: 8px; background: white; }
            QSlider::groove:horizontal { height: 5px; background: #E1E4E8; border-radius: 2px; }
            QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px; background: #6574E8; }
        """)
        self._update_preview()

    def _opacity_changed(self, value: int) -> None:
        self.opacity_value.setText(f"{value}%")
        self.manager.theme.set_opacity(value)
        self._update_preview()

    def _select_theme(self, key: str) -> None:
        self.manager.theme.set_theme(key)
        self._update_preview()

    def _update_preview(self) -> None:
        theme = self.manager.theme.current
        opacity = self.manager.theme.opacity if self.glass_check.isChecked() else 100
        alpha = round(255 * opacity / 100)
        color = theme.accent_soft.lstrip("#")
        red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
        self.preview.setStyleSheet(f"""
            QFrame#glassPreview {{ background: rgba({red}, {green}, {blue}, {alpha}); border: 1px solid {theme.accent}; border-radius: 9px; }}
            QLabel#previewTitle {{ background: transparent; color: #252A34; font-weight: 700; }}
            QLabel#previewHint {{ background: transparent; color: #59616D; }}
        """)
        self.preview_hint.setText(f"背景 {opacity}%")
