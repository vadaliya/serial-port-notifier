import sys
import platform
import traceback
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSharedMemory
from utils.storage import ConfigManager
from core.monitor import SerialMonitor
from ui.tray import TrayApp
from utils.autostart import set_autostart

def exception_hook(exctype, value, tb):
    """Global handler for uncaught exceptions. Writes to a log file."""
    if platform.system() == "Windows":
        base_path = Path(os.getenv("APPDATA", Path.home()))
    else:
        base_path = Path.home() / ".config"
    log_dir = base_path / "SerialPortNotifier"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "crash.log"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    log_entry = f"=== CRASH LOG - {timestamp} ===\n{err_msg}\n"
    
    try:
        with open(log_file, "a") as f:
            f.write(log_entry)
    except Exception:
        pass
        
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

def _show_already_running_warning():
    """Displays a warning pop-up styled with the application logo icon."""
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtCore import Qt
    from utils.helpers import get_resource_path
    
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Serial Port Notifier")
    msg_box.setText("Serial Port Notifier is already running.")
    
    # Resolve the path to the logo based on the platform
    if platform.system() == "Windows":
        icon_path = get_resource_path("assets/logo.ico")
    else:
        icon_path = get_resource_path("assets/logo.png")
        
    # Set the window/taskbar icon
    msg_box.setWindowIcon(QIcon(icon_path))
    
    # Set the main pop-up icon using a high-resolution pixmap extracted from the icon
    icon = QIcon(icon_path)
    high_res_pixmap = icon.pixmap(512, 512)
    if not high_res_pixmap.isNull():
        scaled_pixmap = high_res_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        msg_box.setIconPixmap(scaled_pixmap)
    else:
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
    msg_box.exec()

def main():
    # Set explicit AppUserModelID on Windows so the taskbar groups and shows the custom icon
    if platform.system() == "Windows":
        import ctypes
        myappid = 'vadaliya.serialportnotifier.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # 1. Initialize the GUI Application
    # We must do this before creating any UI elements.
    app = QApplication(sys.argv)
    
    # Enforce single instance
    shared_mem = QSharedMemory("vadaliya.serialportnotifier.singleinstance")
    if shared_mem.attach():
        _show_already_running_warning()
        sys.exit(0)
        
    if not shared_mem.create(1):
        if shared_mem.attach():
            _show_already_running_warning()
            sys.exit(0)
    
    app.setApplicationName("Serial Port Notifier")
    app.setApplicationDisplayName("Serial Port Notifier")
    
    # Optional: Prevents the app from closing if the tray menu closes
    app.setQuitOnLastWindowClosed(False)

    # 2. Initialize Core Engine
    config = ConfigManager()
    
    # Update autostart registration path if enabled to handle app relocation
    prefs = config.get("preferences", {})
    if prefs.get("autostart_enabled", False):
        set_autostart(True)
    
    # Pass None for callbacks initially; TrayApp will hook into them
    monitor = SerialMonitor(config_manager=config)
    
    # 3. Initialize the Tray UI and wire it to the monitor
    tray_app = TrayApp(config_manager=config, monitor=monitor)
    
    # 4. Start the background monitoring thread
    monitor.start()
    
    # 5. Run the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()