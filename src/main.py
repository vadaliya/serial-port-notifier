import sys
import platform
from PyQt6.QtWidgets import QApplication
from utils.storage import ConfigManager
from core.monitor import SerialMonitor
from ui.tray import TrayApp

def main():
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