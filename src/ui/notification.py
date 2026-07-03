import platform
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from utils.helpers import get_resource_path

class ToastNotification(QWidget):
    def __init__(self, title, message, config_manager):
        super().__init__()
        self.config = config_manager.get("notifications", {})
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.timeout_ms = self.config.get("timeout_seconds", 5) * 1000

        self._setup_ui(title, message)
        self._position_on_screen()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        if self.timeout_ms > 0:
            self.timer.start(self.timeout_ms)

    def _get_theme_colors(self):
        """Returns (bg_color, text_color) based on user config or inverted OS theme."""
        custom_bg = self.config.get("custom_bg_color", "")
        custom_text = self.config.get("custom_text_color", "")
        
        if custom_bg and custom_text:
            return custom_bg, custom_text

        # Detect if OS is in Dark Mode (Lightness < 128 means dark)
        is_dark_os = QApplication.palette().window().color().lightness() < 128
        
        # Invert the theme: OS Dark -> Toast Light, OS Light -> Toast Dark
        if is_dark_os:
            return "#F0F0F0", "#1E1E1E" # Light theme toast
        else:
            return "#2D2D30", "#E8E8E8" # Dark theme toast

    def _setup_ui(self, title, message):
        bg_color, text_color = self._get_theme_colors()
        
        # Set OS-specific font
        font_family = "Segoe UI" if platform.system() == "Windows" else "Ubuntu"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("ToastContainer")
        container.setStyleSheet(f"""
            #ToastContainer {{
                background-color: {bg_color};
                border: 1px solid #707070;
                border-radius: 8px;
            }}
            QLabel {{ color: {text_color}; font-family: "{font_family}"; }}
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 12, 15, 15)

        # Header Layout
        header_layout = QHBoxLayout()
        
        # 1. Icon
        icon_label = QLabel()
        pixmap = QPixmap(get_resource_path("assets/logo.png")).scaled(
            18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)
        
        # 2. Title
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # 3. Close Button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {text_color}; border: none; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ color: #FF5050; }}
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        container_layout.addLayout(header_layout)

        # Message Body
        msg_label = QLabel(message)
        msg_label.setStyleSheet("font-size: 13px; margin-top: 2px;")
        msg_label.setWordWrap(True)
        container_layout.addWidget(msg_label)

        layout.addWidget(container)
        self.setLayout(layout)
        self.setFixedSize(300, 100)

    def _position_on_screen(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geometry.width() - self.width() - 20, screen_geometry.height() - self.height() - 20)