import platform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFormLayout, QCheckBox, QGroupBox, QComboBox, QWidget)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from utils.helpers import get_resource_path

class RenamePortDialog(QDialog):
    def __init__(self, device_path, current_label="", marquee_enabled=False, device_info=None, busy_settings=None, parent=None):
        super().__init__(parent)
        self.device_path = device_path
        self.device_info = device_info or {}
        self.initial_marquee = marquee_enabled
        self.initial_busy_settings = busy_settings or {"enabled": False, "interval_ms": 5000}
        
        self.setWindowTitle(f"Port Settings - {device_path}")
        self.setMinimumWidth(440)
        
        icon_file = "logo.ico" if platform.system() == "Windows" else "logo.png"
        self.setWindowIcon(QIcon(get_resource_path(f"assets/{icon_file}")))
        
        self._setup_ui(current_label)
        
    def _setup_ui(self, current_label):
        layout = QVBoxLayout(self)
        
        # Hardware info section
        desc = self.device_info.get("description", "Unknown Device")
        mfg = self.device_info.get("manufacturer", "Unknown")
        
        lbl_info = QLabel(f"<b>Device:</b> {self.device_path}<br/><b>Description:</b> {desc}<br/><b>Manufacturer:</b> {mfg}")
        lbl_info.setStyleSheet("color: #555555; margin-bottom: 6px;")
        layout.addWidget(lbl_info)
        
        # --- 1. Custom Label Group Box ---
        grp_label = QGroupBox("Custom Label")
        grp_label_layout = QVBoxLayout(grp_label)
        
        label_input_layout = QHBoxLayout()
        self.txt_label = QLineEdit(current_label)
        self.txt_label.setMaxLength(30)
        self.txt_label.setPlaceholderText("e.g. My Arduino Uno (Max 30 chars)")
        label_input_layout.addWidget(self.txt_label)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Clear custom label for this port")
        self.btn_clear.clicked.connect(self._clear_label)
        label_input_layout.addWidget(self.btn_clear)
        
        grp_label_layout.addLayout(label_input_layout)
        
        # Marquee Checkbox (shown conditionally)
        self.chk_marquee = QCheckBox("Enable marquee/scrolling text in tray menu")
        self.chk_marquee.setChecked(self.initial_marquee)
        grp_label_layout.addWidget(self.chk_marquee)
        
        # Connect text change to conditionally show/hide the marquee checkbox
        self.txt_label.textChanged.connect(self._on_text_changed)
        self._on_text_changed(current_label)
        
        layout.addWidget(grp_label)
        
        # --- 2. Port Status Probing Group Box ---
        grp_status = QGroupBox("Port Status Indicator (Busy Check)")
        grp_layout = QVBoxLayout(grp_status)
        
        self.chk_busy = QCheckBox("Enable background busy/locked status check for this port")
        self.chk_busy.setChecked(self.initial_busy_settings.get("enabled", False))
        grp_layout.addWidget(self.chk_busy)
        
        # Info & Warning Banner
        lbl_warning = QLabel(
            "<b>Note & Warning:</b><br/>"
            "This periodically probes the serial port to detect if another application is using it.<br/>"
            "<i>Drawback:</i> Probing virtual USB CDC ACM ports (such as nRF5, Arduino, ESP32 microcontrollers) "
            "sends serial connection control signals, which can cause continuous <code>PORT_OPEN / PORT_CLOSE</code> logs, "
            "unintended resets, or serial stream interruptions. Enable with care."
        )
        lbl_warning.setWordWrap(True)
        lbl_warning.setStyleSheet(
            "background-color: #fffbe6; border: 1px solid #ffe58f; "
            "padding: 8px; border-radius: 4px; color: #8c6b00; font-size: 11px; margin-top: 4px; margin-bottom: 6px;"
        )
        grp_layout.addWidget(lbl_warning)
        
        # Interval selection
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Busy Check Interval:"))
        self.combo_busy_interval = QComboBox()
        self.combo_busy_interval.addItem("1 second", 1000)
        self.combo_busy_interval.addItem("2 seconds", 2000)
        self.combo_busy_interval.addItem("5 seconds (Recommended)", 5000)
        self.combo_busy_interval.addItem("10 seconds", 10000)
        self.combo_busy_interval.addItem("15 seconds", 15000)
        
        cur_interval = self.initial_busy_settings.get("interval_ms", 5000)
        idx = self.combo_busy_interval.findData(cur_interval)
        if idx >= 0:
            self.combo_busy_interval.setCurrentIndex(idx)
        else:
            self.combo_busy_interval.setCurrentIndex(2) # Default 5s
            
        interval_layout.addWidget(self.combo_busy_interval)
        interval_layout.addStretch()
        
        self.interval_container = QWidget()
        self.interval_container.setLayout(interval_layout)
        grp_layout.addWidget(self.interval_container)
        
        # Connect checkbox to enable/disable interval container
        self.chk_busy.toggled.connect(self._on_busy_toggled)
        self._on_busy_toggled(self.chk_busy.isChecked())
        
        layout.addWidget(grp_status)
        
        # Buttons (OK, Cancel)
        btn_layout = QHBoxLayout()
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

    def _on_busy_toggled(self, checked):
        self.interval_container.setEnabled(checked)

    def _clear_label(self):
        self.txt_label.clear()

    def get_label(self):
        return self.txt_label.text().strip()

    def get_marquee_enabled(self):
        # Use text length instead of isVisible() since isVisible() becomes False after the dialog closes
        return self.chk_marquee.isChecked() if len(self.get_label()) > 10 else False

    def get_busy_settings(self):
        return {
            "enabled": self.chk_busy.isChecked(),
            "interval_ms": self.combo_busy_interval.currentData()
        }


