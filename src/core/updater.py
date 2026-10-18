import json
import os
import platform
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, QStandardPaths
from version import __version__, GITHUB_LATEST_RELEASE_API, GITHUB_RELEASES_URL

def parse_version(v_str: str) -> tuple:
    """Parses a version string like 'v1.4.0' or '1.3.0' into an integer tuple."""
    if not v_str:
        return (0, 0, 0)
    v_clean = v_str.lstrip("vV").strip()
    parts = re.findall(r"\d+", v_clean)
    return tuple(int(p) for p in parts) if parts else (0, 0, 0)

def is_newer_version(latest_str: str, current_str: str) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    latest_tuple = parse_version(latest_str)
    current_tuple = parse_version(current_str)
    
    max_len = max(len(latest_tuple), len(current_tuple))
    latest_padded = latest_tuple + (0,) * (max_len - len(latest_tuple))
    current_padded = current_tuple + (0,) * (max_len - len(current_tuple))
    
    return latest_padded > current_padded

def find_best_asset(assets: list, target_os: str = None, target_arch: str = None) -> dict | None:
    """
    Selects the most suitable release asset for the current OS and CPU architecture.
    Prefers installers (.exe setup on Windows, .deb on Linux) over portable binaries.
    """
    if target_os is None:
        target_os = platform.system().lower()
    else:
        target_os = target_os.lower()
        
    if target_arch is None:
        is_64 = sys.maxsize > 2**32
        machine = platform.machine().lower()
        is_arm = "arm" in machine or "aarch64" in machine
        target_arch = "arm64" if is_arm else ("x64" if is_64 else "x32")
    else:
        target_arch = target_arch.lower()

    best_asset = None
    best_score = -1

    for asset in assets:
        name = asset.get("name", "").lower()
        score = 0

        if target_os == "windows" and "windows" in name:
            score += 10
            if target_arch in name or (target_arch == "x32" and "x86" in name):
                score += 20
            if name.endswith("-setup.exe"):
                score += 15
            elif name.endswith(".exe"):
                score += 5
        elif target_os == "linux" and "linux" in name:
            score += 10
            if target_arch in name or (target_arch == "x64" and "amd64" in name):
                score += 20
            if name.endswith(".deb"):
                score += 15
            elif not name.endswith(".deb"):
                score += 5

        if score > best_score and score > 0:
            best_score = score
            best_asset = asset

    return best_asset

def get_default_download_directory() -> Path:
    """Returns the user's Downloads directory, or falls back to user home."""
    qt_download_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    if qt_download_dir and os.path.exists(qt_download_dir):
        return Path(qt_download_dir)
    fallback = Path.home() / "Downloads"
    if fallback.exists():
        return fallback
    return Path.home()

def check_for_updates(current_version: str = __version__) -> dict:
    """
    Queries GitHub API for the latest release.
    Returns a dictionary containing update details and matched asset info.
    """
    req = urllib.request.Request(
        GITHUB_LATEST_RELEASE_API,
        headers={"User-Agent": "SerialPortNotifier"}
    )
    
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
        
    tag_name = data.get("tag_name", "")
    latest_version = tag_name.lstrip("vV")
    release_name = data.get("name") or tag_name
    release_notes = data.get("body", "").strip()
    html_url = data.get("html_url", GITHUB_RELEASES_URL)
    published_at = data.get("published_at", "")
    assets = data.get("assets", [])
    
    has_update = is_newer_version(latest_version, current_version)
    matched_asset = find_best_asset(assets)
    
    return {
        "has_update": has_update,
        "current_version": current_version,
        "latest_version": latest_version,
        "tag_name": tag_name,
        "release_name": release_name,
        "release_notes": release_notes,
        "html_url": html_url,
        "published_at": published_at,
        "matched_asset": matched_asset,
        "all_assets": assets
    }

class CheckUpdateThread(QThread):
    """Background worker to check for updates without blocking the UI thread."""
    finished_signal = pyqtSignal(bool, object, str) # (success, update_info, error_msg)

    def __init__(self, current_version: str = __version__, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            update_info = check_for_updates(self.current_version)
            self.finished_signal.emit(True, update_info, "")
        except urllib.error.URLError as e:
            self.finished_signal.emit(False, None, f"Network error: {e.reason}")
        except Exception as e:
            self.finished_signal.emit(False, None, str(e))

class DownloadUpdateThread(QThread):
    """Background worker to download release asset with real-time progress."""
    progress_signal = pyqtSignal(int, int) # (downloaded_bytes, total_bytes)
    finished_signal = pyqtSignal(bool, str, str) # (success, dest_path, error_msg)

    def __init__(self, download_url: str, destination_path: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.destination_path = destination_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        temp_dest = self.destination_path + ".part"
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "SerialPortNotifier"}
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_dest, "wb") as out_file:
                content_len = resp.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len and content_len.isdigit() else 0
                
                downloaded_bytes = 0
                chunk_size = 64 * 1024 # 64 KB chunks
                
                while not self._is_cancelled:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    self.progress_signal.emit(downloaded_bytes, total_bytes)

            if self._is_cancelled:
                if os.path.exists(temp_dest):
                    os.remove(temp_dest)
                self.finished_signal.emit(False, "", "Download was cancelled.")
                return

            # Rename .part file to final destination
            if os.path.exists(self.destination_path):
                os.remove(self.destination_path)
            os.rename(temp_dest, self.destination_path)
            
            self.finished_signal.emit(True, self.destination_path, "")

        except Exception as e:
            if os.path.exists(temp_dest):
                try:
                    os.remove(temp_dest)
                except Exception:
                    pass
            self.finished_signal.emit(False, "", str(e))

