import time
import threading
import platform
import ctypes
import serial
import serial.tools.list_ports

class SerialMonitor:
    def __init__(self, config_manager, on_port_added=None, on_port_removed=None):
        self.config = config_manager
        # Callbacks triggered when a change is detected
        self.on_port_added = on_port_added
        self.on_port_removed = on_port_removed
        self.on_baseline_ready = None
        
        self.running = False
        self.thread = None
        self.current_ports = {}  # Mapped by device name (e.g., 'COM4' or '/dev/ttyUSB0')
        self.last_busy_check_times = {} # Mapped by device name -> timestamp
        self.wake_event = threading.Event()
        self._is_first_poll = True

    def start(self):
        """Start the background polling thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the background polling thread."""
        self.running = False
        self.wake_event.set()
        if self.thread:
            self.thread.join()

    def trigger_poll(self):
        """Force the background thread to poll ports immediately."""
        self.wake_event.set()

    def _monitor_loop(self):
        """Main loop: Poll ports, then sleep for the configured interval."""
        while self.running:
            self._poll_ports()
            interval_ms = self.config.get("preferences", {}).get("polling_interval_ms", 2000)
            # Wait on event, returns True if set, False if timeout.
            # Enforce absolute minimum 500ms to protect CPU.
            self.wake_event.wait(max(0.5, interval_ms / 1000.0))
            self.wake_event.clear()

    def _poll_ports(self):
        """Check hardware and calculate additions/removals."""
        raw_ports = serial.tools.list_ports.comports()
        hidden_ports = self.config.get("hidden_ports", [])
        features_config = self.config.get("preferences", {}).get("features", {})
        global_status_indicator = features_config.get("show_status_indicator", False)
        port_busy_settings = self.config.get("port_busy_settings", {})
        
        now = time.time()
        new_port_state = {}
        
        for p in raw_ports:
            # Skip user-blacklisted ports
            if p.device in hidden_ports:
                continue
            
            # Extract basic data
            port_data = {
                "device": p.device,
                "description": p.description,
                "manufacturer": p.manufacturer or "Unknown",
                "vid": p.vid,
                "pid": p.pid,
                "is_busy": False
            }
            
            # Check availability if status indicator is enabled globally or for this specific port
            port_cfg = port_busy_settings.get(p.device, {})
            is_probing_enabled = global_status_indicator or port_cfg.get("enabled", False)
            
            if is_probing_enabled and not self._is_bluetooth_port(p):
                if p.device in self.current_ports:
                    interval_sec = port_cfg.get("interval_ms", 5000) / 1000.0
                    last_check = self.last_busy_check_times.get(p.device, 0)
                    
                    if (now - last_check) >= interval_sec:
                        port_data["is_busy"] = self._check_if_busy(p.device)
                        self.last_busy_check_times[p.device] = now
                    else:
                        # Carry forward previous busy status until next interval
                        port_data["is_busy"] = self.current_ports[p.device].get("is_busy", False)
                else:
                    # Newly connected port: assume not busy on discovery
                    port_data["is_busy"] = False

            new_port_state[p.device] = port_data

        # If first poll, establish baseline state and alert UI to rebuild menu without notifications
        if self._is_first_poll:
            self.current_ports = new_port_state
            self._is_first_poll = False
            if self.on_baseline_ready:
                self.on_baseline_ready()
            return

        # Detect Added Ports (In new state, but not in old state)
        added_ports = [new_port_state[d] for d in new_port_state if d not in self.current_ports]
        if added_ports and self.on_port_added:
            self.on_port_added(added_ports)

        # Detect Removed Ports (In old state, but not in new state)
        removed_ports = [self.current_ports[d] for d in self.current_ports if d not in new_port_state]
        if removed_ports and self.on_port_removed:
            self.on_port_removed(removed_ports)

        # Update current state
        self.current_ports = new_port_state

    def _is_bluetooth_port(self, p):
        """Identifies Bluetooth serial links by description or manufacturer."""
        desc = (p.description or "").lower()
        mfg = (p.manufacturer or "").lower()
        return "bluetooth" in desc or "bluetooth" in mfg

    def _check_if_busy(self, device):
        """Checks if port is locked by another app. Uses non-intrusive Win32 Query handle on Windows."""
        if platform.system() == "Windows":
            try:
                device_path = "\\\\.\\" + device.strip() if not device.startswith("\\\\.\\") else device
                # dwDesiredAccess = 0 (Query access only - no read/write stream opened, no DTR/RTS or CDC ACM line changes)
                handle = ctypes.windll.kernel32.CreateFileW(device_path, 0, 0, None, 3, 0x80, None)
                if handle == -1 or handle == 0xFFFFFFFF:
                    err = ctypes.windll.kernel32.GetLastError()
                    # Error 5 = ERROR_ACCESS_DENIED, 32 = ERROR_SHARING_VIOLATION
                    if err in (5, 32):
                        return True
                    return True
                else:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return False
            except Exception:
                pass
                
        # Fallback for Linux/macOS or if Win32 check raises an unexpected exception
        try:
            s = serial.Serial(device, timeout=0)
            s.close()
            return False
        except serial.SerialException:
            return True
        except Exception:
            return True