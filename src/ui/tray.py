import sys
import subprocess
import re
import shlex
import platform

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt

# Import our helper
from utils.helpers import get_resource_path
from ui.notification import ToastNotification
from ui.settings_dialog import SettingsDialog

class TrayApp(QObject):
    ports_added_signal = pyqtSignal(list)
    ports_removed_signal = pyqtSignal(list)

    def __init__(self, config_manager, monitor):
        super().__init__()
        self.config = config_manager
        self.monitor = monitor
        self.active_toasts = [] # keep notifications alive in memory
        
        self.monitor.on_port_added = self.ports_added_signal.emit
        self.monitor.on_port_removed = self.ports_removed_signal.emit
        self.ports_added_signal.connect(self._on_ports_added)
        self.ports_removed_signal.connect(self._on_ports_removed)

        self.tray_icon = QSystemTrayIcon()
        
        # --- NEW ICON LOADING LOGIC ---
        # Resolve the path to the logo in the assets folder
        icon_path = get_resource_path("assets/logo.png")
        self.tray_icon.setIcon(QIcon(icon_path))
        # ------------------------------
        
        self.tray_icon.setToolTip("Serial Port Notifier")
        
        self.menu = QMenu()
        self._build_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def _build_menu(self):
        """Clears and rebuilds the right-click menu based on active ports."""
        self.menu.clear()

        # 1. Active Ports Section
        ports = self.monitor.current_ports
        if not ports:
            empty_action = QAction("No Ports Detected", self)
            empty_action.setEnabled(False)
            self.menu.addAction(empty_action)
        else:
            # Sort newest first based on how they were discovered (dict order)
            for device_path, data in reversed(ports.items()):
                self._add_port_menu_item(device_path, data)

        self.menu.addSeparator()

        # 2. Application Controls Section
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings)
        self.menu.addAction(settings_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._open_about)
        self.menu.addAction(about_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._exit_app)
        self.menu.addAction(exit_action)

    def _add_port_menu_item(self, device_path, data):
        """Creates a submenu for an individual port."""
        custom_labels = self.config.get("custom_labels", {})
        display_name = custom_labels.get(device_path, device_path)
        
        if data.get("is_busy"):
            display_name = f"{display_name} (Busy)"
            
        port_menu = self.menu.addMenu(display_name)
        
        # --- 1. Quick Copy Feature ---
        copy_action = QAction(f"Copy '{device_path}'", self)
        copy_action.triggered.connect(lambda checked, p=device_path: self._copy_to_clipboard(p))
        port_menu.addAction(copy_action)
        port_menu.addSeparator()
        
        # --- 2. Launchers Feature ---
        launchers = self.config.get("launchers", [])
        if not launchers:
            empty_action = QAction("No launchers configured", self)
            empty_action.setEnabled(False)
            port_menu.addAction(empty_action)
        else:
            for launcher in launchers:
                action = QAction(launcher.get("label", "Unknown Launcher"), self)
                # Disable clicking if the port is busy
                action.setEnabled(not data.get("is_busy"))
                action.triggered.connect(lambda checked, p=device_path, l=launcher: self._execute_launcher(p, l))
                port_menu.addAction(action)

        port_menu.addSeparator()
        
        # Placeholder for Reset functionality (Phase 5)
        reset_action = QAction("Reset Device (DTR/RTS)", self)
        reset_action.setEnabled(not data.get("is_busy"))
        port_menu.addAction(reset_action)

    def _copy_to_clipboard(self, text):
        """Copies the port name to the OS clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Briefly notify the user so they know it worked
        self._show_notification("Copied to Clipboard", [{"device": text}])

    def _execute_launcher(self, port_name, launcher_config):
        """Executes a third-party application with dynamic port arguments."""
        program = launcher_config.get("program", "")
        args_template = launcher_config.get("args", "")
        
        if not program:
            return

        # Extract just the port number (e.g., "COM4" -> "4", "/dev/ttyUSB0" -> "0")
        match = re.search(r'\d+', port_name)
        port_number = match.group() if match else ""
        
        # Replace placeholders: %1 is full port name, %2 is port number
        args = args_template.replace("%1", port_name).replace("%2", port_number)
        
        try:
            if platform.system() == "Windows":
                # Windows handles string-based commands better for paths with spaces
                full_command = f'"{program}" {args}'
                subprocess.Popen(full_command, shell=False)
            else:
                # Linux/Ubuntu prefers a strictly parsed list
                command_list = [program] + shlex.split(args)
                subprocess.Popen(command_list)
        except Exception as e:
            self._show_notification("Launcher Error", [{"device": str(e)}])

    def _on_ports_changed(self, changed_ports):
        """Triggered safely on the main thread when ports are added/removed."""
        # For now, just rebuild the menu. (Notifications come in Phase 3!)
        self._build_menu()

    def _open_settings(self):
        # Create and show the dialog
        dialog = SettingsDialog(self.config)
        
        # If the user clicks OK (accepts the dialog), rebuild the menu to reflect changes
        if dialog.exec():
            self._build_menu()

    def _open_about(self):
        print("About window will open here")

    def _exit_app(self):
        self.monitor.stop()
        QApplication.quit()
        sys.exit()
    
    def _on_ports_added(self, added_ports):
        self._build_menu()
        self._show_notification("New Serial Ports:", added_ports)

    def _on_ports_removed(self, removed_ports):
        self._build_menu()
        self._show_notification("Serial Ports Removed:", removed_ports)

    def _show_notification(self, title, ports_list):
        notif_config = self.config.get("notifications", {})
        if not notif_config.get("enabled", True):
            return

        port_names = [p.get("device") for p in ports_list]
        message = "\n".join(port_names)
        
        use_native = notif_config.get("use_native_os", True)

        if use_native:
            # Route to OS native notification system (Windows Action Center / Ubuntu Notifier)
            timeout_ms = notif_config.get("timeout_seconds", 5) * 1000
            
            icon_path = get_resource_path("assets/logo.png")
            self.tray_icon.showMessage(
                title, 
                message, 
                QIcon(icon_path), 
                timeout_ms
            )
        else:
            # Route to our Custom PyQt Fallback Toast
            toast = ToastNotification(title, message, self.config)
            toast.show()
            self.active_toasts.append(toast)
            toast.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            toast.destroyed.connect(lambda: self._cleanup_toast(toast))

    def _cleanup_toast(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)