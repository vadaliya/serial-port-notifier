from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout, QCheckBox
from PyQt6.QtCore import Qt

class RenamePortDialog(QDialog):
    def __init__(self, device_path, current_label="", marquee_enabled=False, device_info=None, parent=None):
        super().__init__(parent)
        self.device_path = device_path
        self.device_info = device_info or {}
        self.initial_marquee = marquee_enabled
        self.setWindowTitle(f"Rename Port - {device_path}")
        self.setMinimumWidth(350)
        
        self._setup_ui(current_label)
        
    def _setup_ui(self, current_label):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Hardware info section
        desc = self.device_info.get("description", "Unknown Device")
        mfg = self.device_info.get("manufacturer", "Unknown")
        
        lbl_info = QLabel(f"<b>Device:</b> {self.device_path}<br/><b>Description:</b> {desc}<br/><b>Manufacturer:</b> {mfg}")
        lbl_info.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(lbl_info)
        
        # Label Input
        self.txt_label = QLineEdit(current_label)
        self.txt_label.setMaxLength(30)
        self.txt_label.setPlaceholderText("e.g. My Arduino Uno (Max 30 chars)")
        form_layout.addRow("Custom Label:", self.txt_label)
        
        # Marquee Checkbox (shown conditionally)
        self.chk_marquee = QCheckBox("Enable marquee/scrolling text in tray menu")
        self.chk_marquee.setChecked(self.initial_marquee)
        form_layout.addRow("", self.chk_marquee)
        
        # Connect text change to conditionally show/hide the checkbox
        self.txt_label.textChanged.connect(self._on_text_changed)
        self._on_text_changed(current_label)
        
        layout.addLayout(form_layout)
        
        # Buttons (OK, Clear, Cancel)
        btn_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton("Clear Label")
        self.btn_clear.clicked.connect(self._clear_label)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setDefault(True)
        btn_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def _on_text_changed(self, text):
        # Show checkbox only if text exceeds 10 characters
        self.chk_marquee.setVisible(len(text.strip()) > 10)

    def _clear_label(self):
        self.txt_label.clear()
        self.accept()

    def get_label(self):
        return self.txt_label.text().strip()

    def get_marquee_enabled(self):
        # Use text length instead of isVisible() since isVisible() becomes False after the dialog closes
        return self.chk_marquee.isChecked() if len(self.get_label()) > 10 else False
