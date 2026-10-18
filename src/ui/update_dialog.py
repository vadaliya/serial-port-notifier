import os
import platform
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTextBrowser, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices

from utils.helpers import get_resource_path
from core.updater import DownloadUpdateThread, get_default_download_directory

class UpdateDialog(QDialog):
    """
    Dialog displaying release notes for a newer application version,
    with options to download, track progress, launch installer, or view on GitHub.
    """
    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.download_thread = None
        self.downloaded_file_path = None
        
        self.setWindowTitle("Software Update - Serial Port Notifier")
        self.setMinimumSize(520, 440)
        self.resize(560, 480)
        
        # Window icon
        icon_file = "assets/logo.ico" if platform.system() == "Windows" else "assets/logo.png"
        self.setWindowIcon(QIcon(get_resource_path(icon_file)))

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Theme-aware colors (respecting dark and light mode)
        is_dark = QApplication.palette().window().color().lightness() < 128
        self.is_dark = is_dark
        notes_bg = "#252526" if is_dark else "#FFFFFF"
        notes_fg = "#E6EDF3" if is_dark else "#24292F"
        notes_border = "#3E3E42" if is_dark else "#D0D7DE"
        secondary_fg = "#CCCCCC" if is_dark else "#57606A"
        link_color = "#58A6FF" if is_dark else "#0969DA"
        code_bg = "#343A40" if is_dark else "#EFF1F3"

        # 1. Header (Logo + Title + Version comparison)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)
        
        logo_label = QLabel()
        icon_file = "assets/logo.png"
        pixmap = QPixmap(get_resource_path(icon_file))
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(logo_label)

        title_layout = QVBoxLayout()
        lbl_heading = QLabel("A new version of Serial Port Notifier is available!")
        lbl_heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(lbl_heading)

        current_ver = self.update_info.get("current_version", "")
        latest_ver = self.update_info.get("latest_version", "")
        lbl_version = QLabel(f"Version <b>v{latest_ver}</b> is available (you have <b>v{current_ver}</b>).")
        lbl_version.setStyleSheet(f"color: {secondary_fg}; font-size: 12px;")
        title_layout.addWidget(lbl_version)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 2. Release Notes Area
        lbl_notes = QLabel("Release Notes:")
        lbl_notes.setStyleSheet("font-weight: bold; margin-top: 4px;")
        layout.addWidget(lbl_notes)

        self.txt_notes = QTextBrowser()
        self.txt_notes.setOpenExternalLinks(True)
        self.txt_notes.document().setDefaultStyleSheet(f"""
            a {{ color: {link_color}; text-decoration: none; }}
            h1, h2, h3, h4 {{ color: {notes_fg}; font-weight: bold; margin-top: 6px; margin-bottom: 4px; }}
            p, li {{ color: {notes_fg}; }}
            code {{ background-color: {code_bg}; color: {notes_fg}; padding: 1px 4px; border-radius: 3px; }}
        """)
        self.txt_notes.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {notes_bg};
                color: {notes_fg};
                border: 1px solid {notes_border};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        notes = self.update_info.get("release_notes", "").strip()
        if notes:
            self.txt_notes.setMarkdown(notes)
        else:
            self.txt_notes.setPlainText("No release notes provided for this version.")
        layout.addWidget(self.txt_notes)

        # 3. Matched Asset Details
        matched_asset = self.update_info.get("matched_asset")
        asset_box = QHBoxLayout()
        if matched_asset:
            asset_name = matched_asset.get("name", "")
            asset_size = matched_asset.get("size", 0)
            size_mb = asset_size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb >= 0.1 else f"{asset_size / 1024:.1f} KB"
            self.lbl_asset = QLabel(f"<b>Package:</b> {asset_name} ({size_str})")
        else:
            self.lbl_asset = QLabel("No direct download package for this architecture. Please view release on GitHub.")
        self.lbl_asset.setStyleSheet(f"font-size: 11px; color: {secondary_fg};")
        asset_box.addWidget(self.lbl_asset)
        asset_box.addStretch()
        layout.addLayout(asset_box)

        # 4. Progress Area (hidden until download starts)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"font-size: 11px; color: {secondary_fg};")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        # 5. Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_github = QPushButton("View on GitHub")
        self.btn_github.clicked.connect(self._open_github)
        btn_layout.addWidget(self.btn_github)

        btn_layout.addStretch()

        self.btn_download = QPushButton("Download Update")
        self.btn_download.setDefault(True)
        if matched_asset:
            self.btn_download.clicked.connect(self._start_download)
        else:
            self.btn_download.setEnabled(False)
        btn_layout.addWidget(self.btn_download)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self._on_close_clicked)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _open_github(self):
        url = self.update_info.get("html_url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _start_download(self):
        matched_asset = self.update_info.get("matched_asset")
        if not matched_asset:
            return
            
        download_url = matched_asset.get("browser_download_url")
        asset_name = matched_asset.get("name")
        if not download_url or not asset_name:
            return

        dest_dir = get_default_download_directory()
        dest_path = dest_dir / asset_name

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Connecting to server...")
        
        self.btn_download.setEnabled(False)
        self.btn_close.setText("Cancel Download")

        self.download_thread = DownloadUpdateThread(download_url, str(dest_path), self)
        self.download_thread.progress_signal.connect(self._on_download_progress)
        self.download_thread.finished_signal.connect(self._on_download_finished)
        self.download_thread.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.lbl_status.setText(f"Downloading: {dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%)")
        else:
            dl_mb = downloaded / (1024 * 1024)
            self.lbl_status.setText(f"Downloading: {dl_mb:.1f} MB...")

    def _on_download_finished(self, success: bool, dest_path: str, error_msg: str):
        if success:
            self.downloaded_file_path = dest_path
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Download complete!")
            self.lbl_status.setStyleSheet(
                "font-size: 11px; color: #4EBE73; font-weight: bold;" if getattr(self, "is_dark", False)
                else "font-size: 11px; color: #008800; font-weight: bold;"
            )
            self.btn_close.setText("Close")
            
            # Offer to run the installer or open folder
            is_windows = platform.system() == "Windows"
            is_installer = is_windows and dest_path.lower().endswith(".exe")
            
            if is_installer:
                self.btn_download.setText("Run Installer")
                self.btn_download.setEnabled(True)
                self.btn_download.clicked.disconnect()
                self.btn_download.clicked.connect(self._launch_installer)
                
                reply = QMessageBox.question(
                    self,
                    "Update Ready",
                    f"Update package has been downloaded successfully:\n\n{dest_path}\n\n"
                    "Would you like to close Serial Port Notifier and launch the installer now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._launch_installer()
            else:
                self.btn_download.setText("Open Folder")
                self.btn_download.setEnabled(True)
                self.btn_download.clicked.disconnect()
                self.btn_download.clicked.connect(self._open_containing_folder)
                
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Update downloaded successfully to:\n\n{dest_path}"
                )
        else:
            self.progress_bar.setVisible(False)
            self.lbl_status.setText(f"Error: {error_msg}")
            self.lbl_status.setStyleSheet(
                "font-size: 11px; color: #FF6B6B;" if getattr(self, "is_dark", False)
                else "font-size: 11px; color: #CC0000;"
            )
            self.btn_download.setEnabled(True)
            self.btn_close.setText("Close")
            if error_msg != "Download was cancelled.":
                QMessageBox.warning(self, "Download Failed", f"Could not complete download:\n\n{error_msg}")

    def _launch_installer(self):
        if self.downloaded_file_path and os.path.exists(self.downloaded_file_path):
            try:
                subprocess.Popen([self.downloaded_file_path], shell=False)
                QApplication.quit()
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "Launch Error", f"Failed to execute installer:\n{e}")

    def _open_containing_folder(self):
        if self.downloaded_file_path:
            folder = os.path.dirname(self.downloaded_file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _on_close_clicked(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait(2000)
        self.reject()

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait(2000)
        event.accept()

