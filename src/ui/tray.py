import sys
import subprocess
import re
import shlex
import platform

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer

# Import our helper
from utils.helpers import get_resource_path
from ui.notification import ToastNotification
from ui.settings_dialog import SettingsDialog
from ui.rename_dialog import RenamePortDialog

class TrayApp(QObject):
    ports_added_signal = pyqtSignal(list)
    ports_removed_signal = pyqtSignal(list)

    def __init__(self, config_manager, monitor):
        super().__init__()
        self.config = config_manager
        self.monitor = monitor
        self.active_toasts = [] # keep notifications alive in memory
        self.active_marquees = {} # stores active marquee menus
        
        # Initialize marquee update timer
        self.marquee_timer = QTimer(self)
        self.marquee_timer.timeout.connect(self._update_marquees)
        
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
        self.menu.setStyleSheet("QMenu { min-width: 140px; }")
        self._build_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

        # --- OS NATIVE HARDWARE DETECTION FOR WINDOWS ---
        if platform.system() == "Windows":
            from PyQt6.QtCore import QAbstractNativeEventFilter
            import ctypes
            import ctypes.wintypes

            class DeviceEventFilter(QAbstractNativeEventFilter):
                def __init__(self, monitor):
                    super().__init__()
                    self.monitor = monitor

                def nativeEventFilter(self, eventType, message):
                    if eventType == b'windows_generic_MSG':
                        addr = int(message)
                        if addr:
                            msg = ctypes.wintypes.MSG.from_address(addr)
                            if msg.message == 0x0219:  # WM_DEVICECHANGE
                                # 0x8000 = DBT_DEVICEARRIVAL, 0x8004 = DBT_DEVICEREMOVECOMPLETE
                                if msg.wParam in (0x8000, 0x8004):
                                    self.monitor.trigger_poll()
                                    # Trigger a delayed backup poll 500ms later to catch ports that register with a slight delay
                                    QTimer.singleShot(500, self.monitor.trigger_poll)
                    return False, 0

            self.device_event_filter = DeviceEventFilter(self.monitor)
            QApplication.instance().installNativeEventFilter(self.device_event_filter)

    def _build_menu(self):
        """Clears and rebuilds the right-click menu based on active ports."""
        self.menu.clear()
        self.active_marquees.clear()
        self.marquee_timer.stop()

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
        
        # Start marquee scrolling timer if there are active marquees
        if self.active_marquees:
            self.marquee_timer.start(300)

    def _add_port_menu_item(self, device_path, data):
        """Creates a submenu for an individual port."""
        custom_labels = self.config.get("custom_labels", {})
        label = custom_labels.get(device_path)
        
        if label:
            base_display_name = f"{label} ({device_path})"
        else:
            base_display_name = device_path
            
        global_marquee = self.config.get("preferences", {}).get("enable_marquee", True)
        local_marquee = self.config.get("marquee_ports", {}).get(device_path, False)
        is_marquee_active = global_marquee and local_marquee and len(base_display_name) > 22
        
        display_name = base_display_name
        if is_marquee_active:
            # Set the initial menu title to a truncated 22-character slice.
            # This prevents the parent QMenu from auto-adjusting its width to the full long text.
            display_name = base_display_name[:22]
        elif len(base_display_name) > 22:
            # Marquee is NOT active, so elide the label to make the total string exactly 22 characters
            suffix = f" ({device_path})"
            avail_chars = 22 - len(suffix)
            if label and avail_chars > 3:
                elided_label = label[:avail_chars - 3] + "..."
                display_name = f"{elided_label}{suffix}"
            else:
                display_name = base_display_name[:22]
            
        if data.get("is_busy"):
            display_name = f"{display_name} (Busy)"
            
        port_menu = self.menu.addMenu(display_name)
        
        if is_marquee_active:
            self.active_marquees[device_path] = {
                "menu": port_menu,
                "text": base_display_name,
                "index": 0,
                "is_busy": data.get("is_busy")
            }
        
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
        
        # --- 3. Rename Feature ---
        rename_action = QAction("Rename Port...", self)
        rename_action.triggered.connect(lambda checked, p=device_path, d=data: self._rename_port(p, d))
        port_menu.addAction(rename_action)
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

    def _rename_port(self, device_path, device_info):
        """Opens the rename port dialog and updates the config if changed."""
        custom_labels = self.config.get("custom_labels", {})
        current_label = custom_labels.get(device_path, "")
        
        marquee_ports = self.config.get("marquee_ports", {})
        current_marquee = marquee_ports.get(device_path, False)
        
        dialog = RenamePortDialog(device_path, current_label, current_marquee, device_info)
        if dialog.exec():
            new_label = dialog.get_label()
            if new_label:
                custom_labels[device_path] = new_label
                marquee_ports[device_path] = dialog.get_marquee_enabled()
            else:
                # If label is empty, remove the customization
                custom_labels.pop(device_path, None)
                marquee_ports.pop(device_path, None)
                
            self.config.save_config()
            self._build_menu()

    def _update_marquees(self):
        """Updates the titles of any long-named submenus with a circular text marquee."""
        for device_path, meta in list(self.active_marquees.items()):
            try:
                menu = meta["menu"]
                base_text = meta["text"]
                i = meta["index"]
                is_busy = meta["is_busy"]
                
                limit = 22
                padded = base_text + "    " # add spaces for padding
                n = len(padded)
                
                rot_index = i % n
                scrolling_text = (padded[rot_index:] + padded[:rot_index])[:limit]
                
                if is_busy:
                    display = f"{scrolling_text} (Busy)"
                else:
                    display = scrolling_text
                    
                menu.setTitle(display)
                meta["index"] += 1
            except Exception:
                pass

    def _on_ports_changed(self, changed_ports):
        """Triggered safely on the main thread when ports are added/removed."""
        # For now, just rebuild the menu. (Notifications come in Phase 3!)
        self._build_menu()

    def _open_settings(self):
        # Create and show the dialog
        dialog = SettingsDialog(self.config)
        
        # If the user clicks OK (accepts the dialog), rebuild the menu to reflect changes
        if dialog.exec():
            self.monitor.trigger_poll()
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

        custom_labels = self.config.get("custom_labels", {})
        port_names = []
        for p in ports_list:
            device = p.get("device")
            label = custom_labels.get(device)
            if label:
                # Elide the custom label if it exceeds 18 chars to ensure it fits on a single line
                elided = label if len(label) <= 18 else label[:10] + "..."
                port_names.append(f"{elided} ({device})")
            else:
                port_names.append(device)
        message = "\n".join(port_names)
        
        use_native = notif_config.get("use_native_os", True)

        if use_native:
            # Route to OS native notification system (Windows Action Center / Ubuntu Notifier)
            timeout_ms = notif_config.get("timeout_seconds", 5) * 1000
            icon_path = get_resource_path("assets/logo.png")
            
            # Show ports one-by-one in individual native notifications
            for p_name in port_names:
                self.tray_icon.showMessage(
                    title, 
                    p_name, 
                    QIcon(icon_path), 
                    timeout_ms
                )
        else:
            # Route to our Custom PyQt Fallback Toast (now supports dynamic height)
            toast = ToastNotification(title, message, self.config)
            toast.show()
            self.active_toasts.append(toast)
            toast.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            toast.destroyed.connect(lambda: self._cleanup_toast(toast))

    def _cleanup_toast(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)