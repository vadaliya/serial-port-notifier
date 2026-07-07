import os
import json
import platform
from pathlib import Path

DEFAULT_CONFIG = {
    "preferences": {
        "autostart_enabled": False,
        "polling_interval_ms": 1000,
        "enable_marquee": True,
        "features": {
            "show_vid_pid": True,
            "show_status_indicator": True,
            "enable_quick_copy": True
        }
    },
    "notifications": {
        "enabled": True,
        "timeout_seconds": 5,
        "use_native_os": False,       # True = Windows Action Center / Ubuntu Notifier
        "custom_bg_color": "",       # e.g., "#FF0000". If empty, uses inverted OS theme
        "custom_text_color": ""      # e.g., "#FFFFFF"
    },
    "custom_labels": {},
    "marquee_ports": {},
    "hidden_ports": [],
    "launchers": [],
    "auto_connect_rules": []
}

class ConfigManager:
    def __init__(self, app_name="SerialPortNotifier"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_path = self.config_dir / "settings.json"
        self.config = self.load_config()

    def _get_config_dir(self):
        """Determine the correct user-level config directory based on OS."""
        if platform.system() == "Windows":
            base_path = Path(os.getenv("APPDATA", Path.home()))
        else: # Linux
            base_path = Path.home() / ".config"
        
        config_dir = base_path / self.app_name
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def load_config(self):
        """Load JSON configuration, falling back to defaults if missing or corrupted."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Recursively merge to ensure new updates/keys are injected
                    return self._merge_dicts(DEFAULT_CONFIG.copy(), user_config)
            except json.JSONDecodeError:
                pass # If corrupted, rebuild from default
        
        self.save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    def save_config(self, config_data=None):
        """Write the current dictionary out to the JSON file."""
        if config_data is not None:
            self.config = config_data
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def _merge_dicts(self, default, user):
        """Helper to deeply merge default settings with user settings."""
        for k, v in user.items():
            if isinstance(v, dict) and k in default:
                default[k] = self._merge_dicts(default[k], v)
            else:
                default[k] = v
        return default