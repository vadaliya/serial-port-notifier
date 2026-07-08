import sys
import os
import platform
from pathlib import Path

def set_autostart(enabled: bool) -> bool:
    """
    Enable or disable autostart for the application.
    On Windows: Uses the registry key HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
    On Linux: Uses ~/.config/autostart/serial-port-notifier.desktop
    Returns True if successful, False otherwise.
    """
    system = platform.system()
    try:
        # Determine executable / command to run
        if getattr(sys, 'frozen', False):
            # Compiled PyInstaller executable
            exec_path = sys.executable
            # Ensure path is quoted if it contains spaces
            exec_cmd = f'"{exec_path}"'
        else:
            # Development mode / running as script
            python_exe = sys.executable
            main_py = os.path.abspath(sys.argv[0])
            exec_cmd = f'"{python_exe}" "{main_py}"'

        if system == "Windows":
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "SerialPortNotifier"
            
            if enabled:
                # Open the run key for writing
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                with key:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exec_cmd)
                print(f"Autostart enabled in Windows registry pointing to: {exec_cmd}")
            else:
                # Try to open key and delete the value if it exists
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    with key:
                        winreg.DeleteValue(key, app_name)
                    print("Autostart disabled in Windows registry")
                except FileNotFoundError:
                    # Already deleted or not set
                    pass
            return True

        elif system == "Linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            desktop_file = autostart_dir / "serial-port-notifier.desktop"
            
            if enabled:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                
                # Try to import and resolve absolute logo path
                icon_path = ""
                try:
                    from utils.helpers import get_resource_path
                    icon_path = get_resource_path("assets/logo.png")
                except Exception:
                    pass
                
                content = f"""[Desktop Entry]
Type=Application
Name=Serial Port Notifier
Comment=Real-time Serial Port monitor and notifier utility
Exec={exec_cmd}
Icon={icon_path}
Terminal=false
Categories=Utility;
"""
                with open(desktop_file, "w") as f:
                    f.write(content)
                
                # Make the desktop file executable
                try:
                    os.chmod(desktop_file, 0o755)
                except Exception:
                    pass
                print(f"Autostart desktop entry created at: {desktop_file}")
            else:
                if desktop_file.exists():
                    desktop_file.unlink()
                print("Autostart desktop entry removed")
            return True

        else:
            print(f"Autostart is not supported on platform: {system}")
            return False

    except Exception as e:
        print(f"Failed to configure autostart (enabled={enabled}): {e}")
        return False
