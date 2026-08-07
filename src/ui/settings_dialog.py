import platform
import copy
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QWidget, QCheckBox, QLabel, QListWidget,
                             QComboBox, QLineEdit, QFormLayout, QGroupBox, QSplitter,
                             QApplication)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
import serial.tools.list_ports

from ui.edit_dialog import EditLauncherDialog
from utils.autostart import set_autostart
from utils.helpers import get_resource_path

class AddHiddenPortDialog(QDialog):
    def __init__(self, already_hidden, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Port to Blacklist")
        self.setMinimumWidth(320)
        self.already_hidden = already_hidden
        self.selected_port = ""
        
        icon_file = "logo.ico" if platform.system() == "Windows" else "logo.png"
        self.setWindowIcon(QIcon(get_resource_path(f"assets/{icon_file}")))
        
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
    def __init__(self, config_manager, monitor=None, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.monitor = monitor
        
        self.launchers_copy = copy.deepcopy(self.config.get("launchers", []))
        self.hidden_ports_copy = copy.deepcopy(self.config.get("hidden_ports", []))
        self.custom_labels_copy = copy.deepcopy(self.config.get("custom_labels", {}))
        self.marquee_ports_copy = copy.deepcopy(self.config.get("marquee_ports", {}))
        self.port_busy_settings_copy = copy.deepcopy(self.config.get("port_busy_settings", {}))
        
        self.active_port_device = None
        
        self.setWindowTitle("Serial Port Notifier - Settings")
        self.setMinimumSize(620, 480)
        
        icon_file = "logo.ico" if platform.system() == "Windows" else "logo.png"
        self.setWindowIcon(QIcon(get_resource_path(f"assets/{icon_file}")))
        
        # Main Layout
        layout = QVBoxLayout(self)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_ports_tab(), "Ports")
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

    def _build_ports_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Pane: Ports List
        left_box = QGroupBox("Select Port")
        left_layout = QVBoxLayout(left_box)
        self.ports_list = QListWidget()
        self.ports_list.currentRowChanged.connect(self._on_port_selection_changed)
        left_layout.addWidget(self.ports_list)
        
        # Refresh Ports Button
        btn_refresh = QPushButton("Refresh Ports")
        btn_refresh.clicked.connect(self._populate_ports_tab)
        left_layout.addWidget(btn_refresh)
        
        layout.addWidget(left_box, stretch=1)
        
        # Right Pane: Selected Port Details & Options
        right_box = QGroupBox("Port Configuration")
        self.right_layout = QVBoxLayout(right_box)
        
        # Hardware Info Label
        self.lbl_port_info = QLabel("Select a port to configure")
        self.lbl_port_info.setStyleSheet("color: #555555; margin-bottom: 4px;")
        self.right_layout.addWidget(self.lbl_port_info)
        
        # Group Box 1: Custom Label
        grp_label = QGroupBox("Custom Label")
        grp_label_layout = QVBoxLayout(grp_label)
        
        lbl_input_lay = QHBoxLayout()
        self.txt_port_label = QLineEdit()
        self.txt_port_label.setMaxLength(30)
        self.txt_port_label.setPlaceholderText("e.g. My Arduino (Max 30 chars)")
        lbl_input_lay.addWidget(self.txt_port_label)
        
        self.btn_port_clear_label = QPushButton("Clear")
        self.btn_port_clear_label.clicked.connect(self._clear_port_label)
        lbl_input_lay.addWidget(self.btn_port_clear_label)
        grp_label_layout.addLayout(lbl_input_lay)
        
        self.chk_port_marquee = QCheckBox("Enable marquee/scrolling text in tray menu")
        grp_label_layout.addWidget(self.chk_port_marquee)
        self.txt_port_label.textChanged.connect(self._on_port_label_text_changed)
        
        self.right_layout.addWidget(grp_label)
        
        # Group Box 2: Port Status Indicator
        grp_status = QGroupBox("Port Status Indicator (Busy Check)")
        grp_status_lay = QVBoxLayout(grp_status)
        
        self.chk_port_busy = QCheckBox("Enable background busy/locked status check for this port")
        grp_status_lay.addWidget(self.chk_port_busy)
        
        lbl_warn = QLabel(
            "<b>Note & Warning:</b> Probing virtual USB CDC ACM ports sends serial connection signals, "
            "which can cause continuous <code>PORT_OPEN / PORT_CLOSE</code> logs or resets on microcontrollers. Enable with care."
        )
        lbl_warn.setWordWrap(True)
        lbl_warn.setStyleSheet(
            "background-color: #fffbe6; border: 1px solid #ffe58f; "
            "padding: 6px; border-radius: 4px; color: #8c6b00; font-size: 11px;"
        )
        grp_status_lay.addWidget(lbl_warn)
        
        interval_lay = QHBoxLayout()
        interval_lay.addWidget(QLabel("Busy Check Interval:"))
        self.combo_port_busy_interval = QComboBox()
        self.combo_port_busy_interval.addItem("1 second", 1000)
        self.combo_port_busy_interval.addItem("2 seconds", 2000)
        self.combo_port_busy_interval.addItem("5 seconds (Recommended)", 5000)
        self.combo_port_busy_interval.addItem("10 seconds", 10000)
        self.combo_port_busy_interval.addItem("15 seconds", 15000)
        interval_lay.addWidget(self.combo_port_busy_interval)
        interval_lay.addStretch()
        
        self.port_interval_container = QWidget()
        self.port_interval_container.setLayout(interval_lay)
        grp_status_lay.addWidget(self.port_interval_container)
        
        self.chk_port_busy.toggled.connect(self.port_interval_container.setEnabled)
        self.right_layout.addWidget(grp_status)
        
        # Group Box 3: Quick Actions
        grp_actions = QGroupBox("Quick Actions")
        act_layout = QHBoxLayout(grp_actions)
        
        self.btn_act_peek = QPushButton("Quick Peek...")
        self.btn_act_peek.clicked.connect(self._run_quick_peek)
        act_layout.addWidget(self.btn_act_peek)
        
        self.btn_act_reset = QPushButton("Reset Device")
        self.btn_act_reset.clicked.connect(self._run_reset_device)
        act_layout.addWidget(self.btn_act_reset)
        
        self.btn_act_copy = QPushButton("Copy Path")
        self.btn_act_copy.clicked.connect(self._run_copy_path)
        act_layout.addWidget(self.btn_act_copy)
        
        self.btn_act_hide = QPushButton("Hide Port")
        self.btn_act_hide.clicked.connect(self._run_hide_port)
        act_layout.addWidget(self.btn_act_hide)
        
        self.right_layout.addWidget(grp_actions)
        self.right_layout.addStretch()
        
        layout.addWidget(right_box, stretch=2)
        
        self._populate_ports_tab()
        return tab

    def _populate_ports_tab(self):
        """Populates the ports list with active connected ports and customized ports."""
        self._sync_active_port_fields_to_copy()
        
        self.ports_list.clear()
        self.port_items_data = {}
        
        raw_ports = serial.tools.list_ports.comports()
        all_devices = set(p.device for p in raw_ports if p.device not in self.hidden_ports_copy)
        all_devices.update(self.custom_labels_copy.keys())
        all_devices.update(self.port_busy_settings_copy.keys())
        
        sorted_devices = sorted(list(all_devices))
        
        for dev in sorted_devices:
            # Match info if active
            hw_info = next((p for p in raw_ports if p.device == dev), None)
            desc = hw_info.description if hw_info else "Disconnected Custom Port"
            mfg = (hw_info.manufacturer or "Unknown") if hw_info else "N/A"
            
            label = self.custom_labels_copy.get(dev, "")
            display_text = f"{dev} ({label})" if label else dev
            
            self.ports_list.addItem(display_text)
            self.port_items_data[dev] = {
                "device": dev,
                "description": desc,
                "manufacturer": mfg,
                "is_connected": hw_info is not None
            }
            
        if self.ports_list.count() > 0:
            self.ports_list.setCurrentRow(0)
        else:
            self.lbl_port_info.setText("No ports connected or configured.")
            self.active_port_device = None

    def _on_port_selection_changed(self, row):
        if row < 0:
            return
            
        self._sync_active_port_fields_to_copy()
        
        devices = sorted(list(self.port_items_data.keys()))
        if row >= len(devices):
            return
            
        dev = devices[row]
        self.active_port_device = dev
        pinfo = self.port_items_data.get(dev, {})
        
        status_str = "Connected" if pinfo.get("is_connected") else "Disconnected"
        self.lbl_port_info.setText(
            f"<b>Device:</b> {dev} ({status_str})<br/>"
            f"<b>Description:</b> {pinfo.get('description')}<br/>"
            f"<b>Manufacturer:</b> {pinfo.get('manufacturer')}"
        )
        
        # Load fields from copy
        cur_label = self.custom_labels_copy.get(dev, "")
        self.txt_port_label.setText(cur_label)
        
        cur_marquee = self.marquee_ports_copy.get(dev, False)
        self.chk_port_marquee.setChecked(cur_marquee)
        self._on_port_label_text_changed(cur_label)
        
        cur_busy = self.port_busy_settings_copy.get(dev, {"enabled": False, "interval_ms": 5000})
        self.chk_port_busy.setChecked(cur_busy.get("enabled", False))
        
        idx = self.combo_port_busy_interval.findData(cur_busy.get("interval_ms", 5000))
        if idx >= 0:
            self.combo_port_busy_interval.setCurrentIndex(idx)
        else:
            self.combo_port_busy_interval.setCurrentIndex(2)
            
        self.port_interval_container.setEnabled(self.chk_port_busy.isChecked())
        
        # Action button availability
        is_conn = pinfo.get("is_connected", False)
        self.btn_act_peek.setEnabled(is_conn)
        self.btn_act_reset.setEnabled(is_conn)
        self.btn_act_copy.setEnabled(True)
        self.btn_act_hide.setEnabled(True)

    def _sync_active_port_fields_to_copy(self):
        """Syncs the right pane widget controls back into memory dictionaries."""
        if not self.active_port_device:
            return
            
        dev = self.active_port_device
        label = self.txt_port_label.text().strip()
        
        if label:
            self.custom_labels_copy[dev] = label
            self.marquee_ports_copy[dev] = self.chk_port_marquee.isChecked() if len(label) > 10 else False
        else:
            self.custom_labels_copy.pop(dev, None)
            self.marquee_ports_copy.pop(dev, None)
            
        busy_enabled = self.chk_port_busy.isChecked()
        if busy_enabled:
            self.port_busy_settings_copy[dev] = {
                "enabled": True,
                "interval_ms": self.combo_port_busy_interval.currentData()
            }
        else:
            self.port_busy_settings_copy.pop(dev, None)

    def _clear_port_label(self):
        self.txt_port_label.clear()

    def _on_port_label_text_changed(self, text):
        self.chk_port_marquee.setVisible(len(text.strip()) > 10)

    def _run_quick_peek(self):
        if self.active_port_device:
            from ui.quick_peek import QuickPeekDialog
            dialog = QuickPeekDialog(self.active_port_device, self.config, parent=self)
            dialog.show()

    def _run_reset_device(self):
        if self.active_port_device:
            from core.serial_reset import reset_serial_device
            success, msg = reset_serial_device(self.active_port_device)
            if not success:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Reset Failed", f"Could not reset {self.active_port_device}: {msg}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Reset Success", f"Hardware reset triggered for {self.active_port_device}")

    def _run_copy_path(self):
        if self.active_port_device:
            QApplication.clipboard().setText(self.active_port_device)

    def _run_hide_port(self):
        if self.active_port_device and self.active_port_device not in self.hidden_ports_copy:
            self.hidden_ports_copy.append(self.active_port_device)
            self.hidden_ports_list.addItem(self.active_port_device)
            self._populate_ports_tab()

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
        for port in self.hidden_ports_copy:
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
        dialog = AddHiddenPortDialog(self.hidden_ports_copy, self)
        if dialog.exec():
            port = dialog.selected_port
            if port and port not in self.hidden_ports_copy:
                self.hidden_ports_copy.append(port)
                self.hidden_ports_list.addItem(port)
                self._populate_ports_tab()
                
    def _remove_hidden_port(self):
        item = self.hidden_ports_list.currentItem()
        if item:
            row = self.hidden_ports_list.row(item)
            self.hidden_ports_list.takeItem(row)
            self.hidden_ports_copy.pop(row)
            self._populate_ports_tab()

    def _populate_launchers(self):
        """Fills the list widget with current launchers from copy."""
        self.launcher_list.clear()
        for launcher in self.launchers_copy:
            label = launcher.get("label", "Unknown")
            program = launcher.get("program", "")
            args = launcher.get("args", "")
            display_text = f"{label} ({program} {args})"
            self.launcher_list.addItem(display_text)

    def _add_launcher(self):
        dialog = EditLauncherDialog(parent=self)
        if dialog.exec():
            self.launchers_copy.append(dialog.get_data())
            self._populate_launchers()

    def _edit_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        dialog = EditLauncherDialog(self.launchers_copy[row], parent=self)
        if dialog.exec():
            self.launchers_copy[row] = dialog.get_data()
            self._populate_launchers()

    def _delete_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        self.launchers_copy.pop(row)
        self._populate_launchers()

    def _duplicate_launcher(self):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        new_launcher = self.launchers_copy[row].copy()
        new_launcher["label"] += " (Copy)"
        new_launcher["id"] = f"launcher_{hash(new_launcher['label'])}"
        
        self.launchers_copy.insert(row + 1, new_launcher)
        self._populate_launchers()
        self.launcher_list.setCurrentRow(row + 1)

    def _move_launcher(self, direction):
        row = self.launcher_list.currentRow()
        if row < 0: return
        
        new_row = row + direction
        if 0 <= new_row < len(self.launchers_copy):
            self.launchers_copy[row], self.launchers_copy[new_row] = self.launchers_copy[new_row], self.launchers_copy[row]
            self._populate_launchers()
            self.launcher_list.setCurrentRow(new_row)

    def _save_and_close(self):
        """Save settings back to config manager and close."""
        self._sync_active_port_fields_to_copy()
        
        # Save General Tab
        prefs = self.config.get("preferences", {})
        
        old_autostart = prefs.get("autostart_enabled", False)
        new_autostart = self.chk_autostart.isChecked()
        if old_autostart != new_autostart:
            set_autostart(new_autostart)
            
        prefs["autostart_enabled"] = new_autostart
        prefs["polling_interval_ms"] = self.combo_interval.currentData()
        prefs["enable_marquee"] = self.chk_marquee.isChecked()
        
        notifs = self.config.get("notifications", {})
        notifs["enabled"] = self.chk_notifications.isChecked()
        
        # Save Port Customizations, Blacklist and Launchers from copies back to config
        self.config.set("custom_labels", self.custom_labels_copy)
        self.config.set("marquee_ports", self.marquee_ports_copy)
        self.config.set("port_busy_settings", self.port_busy_settings_copy)
        self.config.set("hidden_ports", self.hidden_ports_copy)
        self.config.set("launchers", self.launchers_copy)
        
        self.config.save_config()
        self.accept()