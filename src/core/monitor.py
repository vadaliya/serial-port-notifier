import time
import threading
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
            
            # Check availability if the user enabled the status indicator
            # Skip Bluetooth ports to avoid massive connection timeouts (5+ seconds) on Windows
            if features_config.get("show_status_indicator", True) and not self._is_bluetooth_port(p):
                # Skip checking if busy on the very first poll it is detected
                # This prevents blocking the thread during driver initialization (which takes 2-3s for some USB-to-Serial chips)
                if p.device in self.current_ports:
                    port_data["is_busy"] = self._check_if_busy(p.device)
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
        """Attempts to briefly open the port to see if another app locked it."""
        try:
            # Non-blocking, instant open/close attempt
            s = serial.Serial(device, timeout=0)
            s.close()
            return False
        except serial.SerialException:
            return True
        except Exception:
            # Catch-all for aggressive Linux permission locks
            return True