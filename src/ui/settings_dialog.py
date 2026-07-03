from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTabWidget, QWidget, QCheckBox, QLabel, QListWidget)
from PyQt6.QtCore import Qt

from ui.edit_dialog import EditLauncherDialog

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
        layout.addWidget(QLabel("Hidden Ports (Blacklist) coming soon..."))
        layout.addStretch()
        return tab

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
        
        notifs = self.config.get("notifications", {})
        notifs["enabled"] = self.chk_notifications.isChecked()
        
        self.config.save_config()
        self.accept()