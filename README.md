# serial-port-notifier
A lightweight, cross-platform (Windows/Linux) desktop utility that monitors serial ports in real-time, notifies you on connection changes, and allows quick actions to copy port names or launch terminal emulators (PuTTY, RealTerm, etc.) with custom arguments.

**🛠️ Development Roadmap: Cross-Platform Serial Port Notifier**

**Phase 1: Project Skeleton & Core Hardware Logic (The Engine)**

* Set up the Python virtual environment and folder structure.

* Create the configuration manager (`utils/storage.py`) to handle reading/writing `settings.json` locally without admin rights.

* Build the background hardware monitor (`core/monitor.py`) using `pyserial` to detect connected ports, grab VID/PID data, and check if a port is "Busy" or "Available".

**Phase 2: UI Foundation & System Tray (The Face)**

* Initialize the main PyQt6 application.

* Create the System Tray Icon and the basic right-click context menu.

* Wire the background hardware monitor to the system tray so the menu dynamically updates (adds/removes ports) in real-time.

**Phase 3: Custom Notifications & Basic Actions (The Voice)**

* Build the custom, cross-platform PyQt Toast Notification system (with auto-hide timeout and a close "X" button).

* Implement the "Quick Copy" feature (clicking a port copies it to the clipboard).

* Build the logic to execute standard third-party Launchers (PuTTY, RealTerm) passing the `%1` and `%2` arguments.

**Phase 4: Configuration UI & Core Settings (The Dashboard)**

* Build the main "Settings" dialog UI.

* Implement the "Launchers" tab (Add, Edit, Delete, Duplicate, Move Up/Down).

* Implement the "Custom Labels/Rename" dialog.

* Implement the "Hidden Ports (Blacklist)" tab.

**Phase 5: Advanced Developer Features - Part 1 (The Tools)**

* Build the "Quick Peek" read-only data monitor window.

* Implement the DTR/RTS "Reset Device" hardware toggle functionality.

* Create the "Auto-Baud Rate Probing" logic.

**Phase 6: Advanced Developer Features - Part 2 (Automation & Networking)**

* Build the Auto-Connect / Script Hook rules engine.

* Implement the TCP/IP Serial Bridge (Port Forwarding) logic.

* Create the Connection Event History (Log) window.

**Phase 7: Polish, Autostart & Packaging (The Finish Line)**

* Add the Settings Export/Import functionality.

* Write the OS-specific Autostart scripts (Windows Startup folder / Ubuntu `.desktop` file).

* Write the `PyInstaller` build script to compile everything into a single, no-admin executable.