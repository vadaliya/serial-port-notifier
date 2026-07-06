from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QWidget, QCheckBox, QLabel, QListWidget,
                             QComboBox, QLineEdit, QFormLayout)
from PyQt6.QtCore import Qt
import serial.tools.list_ports

from ui.edit_dialog import EditLauncherDialog

class AddHiddenPortDialog(QDialog):
    def __init__(self, already_hidden, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Port to Blacklist")
        self.setMinimumWidth(320)
        self.already_hidden = already_hidden
        self.selected_port = ""
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select an active port to hide:"))
        
        # Combo box for active ports
        self.combo_ports = QComboBox()
        self.combo_ports.addItem("-- Select Connected Port --", "")
        
        active_ports = serial.tools.list_ports.comports()
        
        for p in active_ports:
            if p.device not in self.already_hidden:
                self.combo_ports.addItem(f"{p.device} ({p.description})", p.device)
                
        layout.addWidget(self.combo_ports)
        
        # Manual entry field
        layout.addWidget(QLabel("Or enter custom port path/name manually:"))
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("e.g. COM1 or /dev/ttyUSB9")
        layout.addWidget(self.txt_custom)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("Add")
        self.btn_ok.clicked.connect(self._on_accept)
        self.btn_ok.setDefault(True)
        btn_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
    def _on_accept(self):
        custom_text = self.txt_custom.text().strip()
        combo_value = self.combo_ports.currentData()
        
        if custom_text:
            self.selected_port = custom_text
            self.accept()
        elif combo_value:
            self.selected_port = combo_value
            self.accept()
        else:
            self.reject()

class SettingsDialog(QDialog):
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        
        self.setWindowTitle("Serial Port Notifier - Settings")
        self.setMinimumSize(500, 400)
        
        # Main Layout
        layout = QVBoxLayout(self)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_launchers_tab(), "Launchers")
        self.tabs.addTab(self._build_hidden_ports_tab(), "Hidden Ports")
        layout.addWidget(self.tabs)
        
        # Bottom Button Box (OK / Cancel)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        prefs = self.config.get("preferences", {})
        notifs = self.config.get("notifications", {})
        
        self.chk_autostart = QCheckBox("Start automatically on system login")
        self.chk_autostart.setChecked(prefs.get("autostart_enabled", False))
        layout.addWidget(self.chk_autostart)
        
        self.chk_notifications = QCheckBox("Show Notifications on Port Changes")
        self.chk_notifications.setChecked(notifs.get("enabled", True))
        layout.addWidget(self.chk_notifications)
        
        self.chk_marquee = QCheckBox("Enable marquee scrolling for long port names globally")
        self.chk_marquee.setChecked(prefs.get("enable_marquee", True))
        layout.addWidget(self.chk_marquee)
        
        # Polling Interval Setting
        form_layout = QFormLayout()
        self.combo_interval = QComboBox()
        self.combo_interval.addItem("Fast (500 ms)", 500)
        self.combo_interval.addItem("Standard (1 second)", 1000)
        self.combo_interval.addItem("Normal (2 seconds)", 2000)
        self.combo_interval.addItem("Slow (5 seconds)", 5000)
        
        current_interval = prefs.get("polling_interval_ms", 1000)
        index = self.combo_interval.findData(current_interval)
        if index >= 0:
            self.combo_interval.setCurrentIndex(index)
        else:
            self.combo_interval.addItem(f"Custom ({current_interval} ms)", current_interval)
            self.combo_interval.setCurrentIndex(self.combo_interval.count() - 1)
            
        form_layout.addRow("Polling Interval:", self.combo_interval)
        
        lbl_help = QLabel("(Note: On Windows, USB insertions are detected instantly using system events. This interval acts as a background fallback.)")
        lbl_help.setStyleSheet("color: #777777; font-size: 11px;")
        
        layout.addSpacing(10)
        layout.addLayout(form_layout)
        layout.addWidget(lbl_help)
        
        layout.addStretch()
        return tab

    def _build_launchers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.launcher_list = QListWidget()
        self._populate_launchers()
        layout.addWidget(self.launcher_list)
        
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("New...")
        self.btn_new.clicked.connect(self._add_launcher)
        
        self.btn_edit = QPushButton("Edit...")
        self.btn_edit.clicked.connect(self._edit_launcher)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self._delete_launcher)

        # Adding the extra buttons from your mockup
        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.clicked.connect(self._duplicate_launcher)
        
        self.btn_up = QPushButton("Move Up")
        self.btn_up.clicked.connect(lambda: self._move_launcher(-1))
        
        self.btn_down = QPushButton("Move Down")
        self.btn_down.clicked.connect(lambda: self._move_launcher(1))
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_duplicate)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        layout.addLayout(btn_layout)
        
        return tab

    def _build_hidden_ports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(QLabel("Ports in this blacklist will be ignored by the monitor and won't appear in the menu."))
        
        self.hidden_ports_list = QListWidget()
        for port in self.config.get("hidden_ports", []):
            self.hidden_ports_list.addItem(port)
            
        layout.addWidget(self.hidden_ports_list)
        
        btn_layout = QHBoxLayout()
        self.btn_add_hidden = QPushButton("Add...")
        self.btn_add_hidden.clicked.connect(self._add_hidden_port)
        
        self.btn_remove_hidden = QPushButton("Remove")
        self.btn_remove_hidden.clicked.connect(self._remove_hidden_port)
        
        btn_layout.addWidget(self.btn_add_hidden)
        btn_layout.addWidget(self.btn_remove_hidden)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return tab

    def _add_hidden_port(self):
        already_hidden = []
        for i in range(self.hidden_ports_list.count()):
            already_hidden.append(self.hidden_ports_list.item(i).text())
            
        dialog = AddHiddenPortDialog(already_hidden, self)
        if dialog.exec():
            port = dialog.selected_port
            if port and port not in already_hidden:
                self.hidden_ports_list.addItem(port)
                
    def _remove_hidden_port(self):
        item = self.hidden_ports_list.currentItem()
        if item:
            self.hidden_ports_list.takeItem(self.hidden_ports_list.row(item))

    def _populate_launchers(self):
        """Fills the list widget with current launchers from config."""
        self.launcher_list.clear()
        for launcher in self.config.get("launchers", []):
            label = launcher.get("label", "Unknown")
            program = launcher.get("program", "")
            args = launcher.get("args", "")
            # Display format matching your screenshot
            display_text = f"{label} ({program} {args})"
            self.launcher_list.addItem(display_text)

    def _add_launcher(self):
        dialog = EditLauncherDialog()
        if dialog.exec():
            launchers = self.config.get("launchers", [])
            launchers.append(dialog.get_data())
            self.config.save_config()
            self._populate_launchers()

    def _edit_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        launchers = self.config.get("launchers", [])
        dialog = EditLauncherDialog(launchers[row])
        if dialog.exec():
            launchers[row] = dialog.get_data()
            self.config.save_config()
            self._populate_launchers()

    def _delete_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        launchers = self.config.get("launchers", [])
        launchers.pop(row)
        self.config.save_config()
        self._populate_launchers()

    def _duplicate_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        launchers = self.config.get("launchers", [])
        new_launcher = launchers[row].copy()
        new_launcher["label"] += " (Copy)"
        new_launcher["id"] = f"launcher_{hash(new_launcher['label'])}"
        
        launchers.insert(row + 1, new_launcher)
        self.config.save_config()
        self._populate_launchers()
        self.launcher_list.setCurrentRow(row + 1)

    def _move_launcher(self, direction):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        new_row = row + direction
        launchers = self.config.get("launchers", [])
        
        if 0 <= new_row < len(launchers):
            # Swap items
            launchers[row], launchers[new_row] = launchers[new_row], launchers[row]
            self.config.save_config()
            self._populate_launchers()
            self.launcher_list.setCurrentRow(new_row)

    def _save_and_close(self):
        """Save settings back to config manager and close."""
        # Save General Tab
        prefs = self.config.get("preferences", {})
        prefs["autostart_enabled"] = self.chk_autostart.isChecked()
        prefs["polling_interval_ms"] = self.combo_interval.currentData()
        prefs["enable_marquee"] = self.chk_marquee.isChecked()
        
        notifs = self.config.get("notifications", {})
        notifs["enabled"] = self.chk_notifications.isChecked()
        
        # Save Hidden Ports Blacklist
        hidden_ports = []
        for i in range(self.hidden_ports_list.count()):
            hidden_ports.append(self.hidden_ports_list.item(i).text())
        self.config.config["hidden_ports"] = hidden_ports
        
        self.config.save_config()
        self.accept()