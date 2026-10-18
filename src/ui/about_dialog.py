import platform
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices

from utils.helpers import get_resource_path
from version import __version__, APP_NAME, APP_AUTHOR, GITHUB_URL

class AboutDialog(QDialog):
    def __init__(self, on_check_update_callback=None, parent=None):
        super().__init__(parent)
        self.on_check_update_callback = on_check_update_callback
        
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(420, 260)
        
        icon_file = "assets/logo.ico" if platform.system() == "Windows" else "assets/logo.png"
        self.setWindowIcon(QIcon(get_resource_path(icon_file)))
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header with Logo and App Info
        header = QHBoxLayout()
        header.setSpacing(16)
        
        lbl_logo = QLabel()
        pixmap = QPixmap(get_resource_path("assets/logo.png"))
        if not pixmap.isNull():
            lbl_logo.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(lbl_logo)

        # Theme-aware colors
        from PyQt6.QtWidgets import QApplication
        is_dark = QApplication.palette().window().color().lightness() < 128
        secondary_fg = "#CCCCCC" if is_dark else "#666666"
        desc_fg = "#DDDDDD" if is_dark else "#444444"
        link_color = "#58A6FF" if is_dark else "#0969DA"

        info_layout = QVBoxLayout()
        lbl_title = QLabel(f"<b>{APP_NAME}</b>")
        lbl_title.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(lbl_title)

        lbl_version = QLabel(f"Version {__version__}")
        lbl_version.setStyleSheet(f"color: {secondary_fg}; font-size: 12px;")
        info_layout.addWidget(lbl_version)

        lbl_author = QLabel(f"Author: {APP_AUTHOR}")
        lbl_author.setStyleSheet(f"color: {secondary_fg}; font-size: 11px;")
        info_layout.addWidget(lbl_author)

        header.addLayout(info_layout)
        header.addStretch()
        layout.addLayout(header)

        # Description
        lbl_desc = QLabel("Real-time Serial Port monitor and notification utility with quick launcher integration.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"margin-top: 5px; color: {desc_fg}; font-size: 11px;")
        layout.addWidget(lbl_desc)

        # GitHub Link
        lbl_link = QLabel(f'<a href="{GITHUB_URL}" style="color: {link_color}; text-decoration: none;">GitHub Repository</a>')
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setStyleSheet("font-size: 11px;")
        layout.addWidget(lbl_link)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        
        if self.on_check_update_callback:
            self.btn_update = QPushButton("Check for Updates...")
            self.btn_update.clicked.connect(self._trigger_update_check)
            btn_layout.addWidget(self.btn_update)
            
        btn_layout.addStretch()
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def _trigger_update_check(self):
        self.accept()
        if self.on_check_update_callback:
            self.on_check_update_callback()

