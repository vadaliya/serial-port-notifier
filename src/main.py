import sys
import platform
import traceback
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from utils.storage import ConfigManager
from core.monitor import SerialMonitor
from ui.tray import TrayApp

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

def main():
    # Set explicit AppUserModelID on Windows so the taskbar groups and shows the custom icon
    if platform.system() == "Windows":
        import ctypes
        myappid = 'vadaliya.serialportnotifier.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # 1. Initialize the GUI Application
    # We must do this before creating any UI elements.
    app = QApplication(sys.argv)
    
    app.setApplicationName("Serial Port Notifier")
    app.setApplicationDisplayName("Serial Port Notifier")
    
    # Optional: Prevents the app from closing if the tray menu closes
    app.setQuitOnLastWindowClosed(False)

    # 2. Initialize Core Engine
    config = ConfigManager()
    
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