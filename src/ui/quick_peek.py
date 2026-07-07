import re
from datetime import datetime
import platform
import serial
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QGroupBox, QPlainTextEdit, QWidget, QFormLayout)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator, QTextCursor, QIcon
from utils.helpers import get_resource_path

class SerialReaderThread(QThread):
    data_received = pyqtSignal(bytes)
    status_changed = pyqtSignal(bool, str)

    def __init__(self, port_path, parent=None):
        super().__init__(parent)
        self.port_path = port_path
        self.baud_rate = 9600
        self.bytesize = 8
        self.parity = 'N'
        self.stopbits = 1
        self.xonxoff = False
        self.rtscts = False
        self.dtr_state = False
        self.rts_state = False
        
        self.poll_interval_ms = 100
        self.reconnect_enabled = False
        self.reconnect_interval_ms = 1000
        
        self._running = False
        self.ser = None

    def set_dtr(self, state):
        self.dtr_state = state
        if self.ser and self.ser.is_open:
            try:
                self.ser.dtr = state
            except Exception:
                pass

    def set_rts(self, state):
        self.rts_state = state
        if self.ser and self.ser.is_open:
            try:
                self.ser.rts = state
            except Exception:
                pass

    def run(self):
        self._running = True
        
        while self._running:
            try:
                self.ser = serial.Serial()
                self.ser.port = self.port_path
                self.ser.baudrate = self.baud_rate
                self.ser.bytesize = self.bytesize
                self.ser.parity = self.parity
                self.ser.stopbits = self.stopbits
                self.ser.xonxoff = self.xonxoff
                self.ser.rtscts = self.rtscts
                self.ser.timeout = 0.05
                self.ser.open()
                
                # Apply initial pin states
                self.ser.dtr = self.dtr_state
                self.ser.rts = self.rts_state
                
                self.status_changed.emit(True, "Connected")
                
                # Reading loop
                while self._running and self.ser.is_open:
                    try:
                        data = self.ser.read(1024)
                        if data:
                            self.data_received.emit(data)
                    except Exception as e:
                        raise e
                        
                    if self.poll_interval_ms > 0:
                        self.msleep(self.poll_interval_ms)
                        
            except Exception as e:
                self.status_changed.emit(False, str(e))
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                    self.ser = None
                
                # Retry reconnect loop if allowed
                if self._running and self.reconnect_enabled:
                    slept = 0
                    while self._running and slept < self.reconnect_interval_ms:
                        self.msleep(50)
                        slept += 50
                else:
                    break
                    
        # Final cleanup
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

class QuickPeekDialog(QDialog):
    closed_signal = pyqtSignal()

    def __init__(self, port_path, config_manager, parent=None):
        super().__init__(parent)
        self.port_path = port_path
        self.config = config_manager
        self.setWindowTitle(f"Quick Peek - {port_path}")
        self.resize(850, 700)
        self.setMinimumSize(800, 600)
        
        # Set Window Icon
        icon_file = "logo.ico" if platform.system() == "Windows" else "logo.png"
        self.setWindowIcon(QIcon(get_resource_path(f"assets/{icon_file}")))
        
        self.byte_buffer = bytearray()
        self.line_counter = 1
        self.is_paused = False
        
        self.reader = SerialReaderThread(port_path, self)
        self.reader.data_received.connect(self._on_data_received)
        self.reader.status_changed.connect(self._on_status_changed)
        self.reader.finished.connect(self.deleteLater)
        
        self._setup_ui()
        self._load_settings()
        self._restart_connection()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- LEFT PANEL: Controls (Width locked) ---
        left_widget = QWidget()
        left_widget.setFixedWidth(260)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status Bar Group
        grp_status = QGroupBox("Status")
        status_lay = QVBoxLayout(grp_status)
        self.lbl_status = QLabel("Disconnected")
        self.lbl_status.setStyleSheet("font-weight: bold; color: red; font-size: 11pt;")
        status_lay.addWidget(self.lbl_status)
        
        # Connect & Disconnect buttons
        btn_conn_lay = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._restart_connection)
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self._disconnect_port)
        self.btn_disconnect.setEnabled(False)
        btn_conn_lay.addWidget(self.btn_connect)
        btn_conn_lay.addWidget(self.btn_disconnect)
        status_lay.addLayout(btn_conn_lay)
        
        left_layout.addWidget(grp_status)
        
        # Config Group
        grp_config = QGroupBox("Serial Configuration")
        config_lay = QFormLayout(grp_config)
        
        self.combo_baud = QComboBox()
        for baud in [9600, 19200, 38400, 57600, 115200, 230400, 921600]:
            self.combo_baud.addItem(str(baud), baud)
        self.combo_baud.setCurrentIndex(4) # default 115200
        self.combo_baud.currentIndexChanged.connect(self._restart_connection)
        config_lay.addRow("Baud Rate:", self.combo_baud)
        
        self.combo_data = QComboBox()
        for bits in [5, 6, 7, 8]:
            self.combo_data.addItem(str(bits), bits)
        self.combo_data.setCurrentIndex(3) # default 8 bits
        self.combo_data.currentIndexChanged.connect(self._restart_connection)
        config_lay.addRow("Data Bits:", self.combo_data)
        
        self.combo_parity = QComboBox()
        self.combo_parity.addItem("None", 'N')
        self.combo_parity.addItem("Even", 'E')
        self.combo_parity.addItem("Odd", 'O')
        self.combo_parity.addItem("Mark", 'M')
        self.combo_parity.addItem("Space", 'S')
        self.combo_parity.currentIndexChanged.connect(self._restart_connection)
        config_lay.addRow("Parity:", self.combo_parity)
        
        self.combo_stop = QComboBox()
        self.combo_stop.addItem("1", 1)
        self.combo_stop.addItem("1.5", 1.5)
        self.combo_stop.addItem("2", 2)
        self.combo_stop.currentIndexChanged.connect(self._restart_connection)
        config_lay.addRow("Stop Bits:", self.combo_stop)
        
        self.combo_flow = QComboBox()
        self.combo_flow.addItem("None", "none")
        self.combo_flow.addItem("RTS/CTS (Hardware)", "rtscts")
        self.combo_flow.addItem("XON/XOFF (Software)", "xonxoff")
        self.combo_flow.addItem("RTS/CTS + XON/XOFF", "combined")
        self.combo_flow.currentIndexChanged.connect(self._restart_connection)
        config_lay.addRow("Flow Control:", self.combo_flow)
        
        left_layout.addWidget(grp_config)
        
        # Pins Group
        grp_pins = QGroupBox("Control Pins")
        pins_lay = QHBoxLayout(grp_pins)
        self.chk_rts = QCheckBox("RTS on")
        self.chk_rts.toggled.connect(self.reader.set_rts)
        self.chk_dtr = QCheckBox("DTR on")
        self.chk_dtr.toggled.connect(self.reader.set_dtr)
        pins_lay.addWidget(self.chk_rts)
        pins_lay.addWidget(self.chk_dtr)
        left_layout.addWidget(grp_pins)
        
        # Reconnect/Monitor Settings Group
        grp_reconn = QGroupBox("Monitoring")
        reconn_lay = QVBoxLayout(grp_reconn)
        
        self.chk_poll = QCheckBox("When connected... monitor every")
        self.chk_poll.setChecked(True)
        self.chk_poll.toggled.connect(self._restart_connection)
        self.txt_poll = QLineEdit("100")
        self.txt_poll.setValidator(QIntValidator(1, 10000))
        self.txt_poll.textChanged.connect(self._restart_connection)
        
        poll_row = QHBoxLayout()
        poll_row.addWidget(self.txt_poll)
        poll_row.addWidget(QLabel("ms"))
        
        self.chk_reconnect = QCheckBox("When disconnected... retry every")
        self.chk_reconnect.setChecked(True)
        self.chk_reconnect.toggled.connect(self._restart_connection)
        self.txt_reconnect = QLineEdit("1000")
        self.txt_reconnect.setValidator(QIntValidator(100, 60000))
        self.txt_reconnect.textChanged.connect(self._restart_connection)
        
        reconn_row = QHBoxLayout()
        reconn_row.addWidget(self.txt_reconnect)
        reconn_row.addWidget(QLabel("ms"))
        
        reconn_lay.addWidget(self.chk_poll)
        reconn_lay.addLayout(poll_row)
        reconn_lay.addWidget(self.chk_reconnect)
        reconn_lay.addLayout(reconn_row)
        left_layout.addWidget(grp_reconn)
        
        # RX formatting
        grp_format = QGroupBox("Rx Formatting")
        format_lay = QFormLayout(grp_format)
        
        self.combo_eol = QComboBox()
        self.combo_eol.addItem("None", "none")
        self.combo_eol.addItem("<CR> (\\r)", b'\r')
        self.combo_eol.addItem("<LF> (\\n)", b'\n')
        self.combo_eol.addItem("<CR><LF> (\\r\\n)", b'\r\n')
        self.combo_eol.addItem("<LF><CR> (\\n\\r)", b'\n\r')
        self.combo_eol.addItem("<NUL> (\\x00)", b'\x00')
        self.combo_eol.addItem("<TAB> (\\t)", b'\t')
        self.combo_eol.addItem("<SPACE> ( )", b' ')
        self.combo_eol.setCurrentIndex(2) # Default to <LF> (\n)
        format_lay.addRow("Rx EOL:", self.combo_eol)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["ASCII", "HEX"])
        format_lay.addRow("Display Mode:", self.combo_mode)
        
        self.chk_line_nums = QCheckBox("Show line number")
        self.chk_timestamps = QCheckBox("Show time stamp")
        self.chk_scroll = QCheckBox("Auto-scroll console")
        self.chk_scroll.setChecked(True)
        
        format_lay.addRow("", self.chk_line_nums)
        format_lay.addRow("", self.chk_timestamps)
        format_lay.addRow("", self.chk_scroll)
        left_layout.addWidget(grp_format)
        
        # Action Buttons
        btn_lay = QHBoxLayout()
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_clear = QPushButton("Clear Log")
        self.btn_clear.clicked.connect(self._clear_log)
        
        btn_lay.addWidget(self.btn_pause)
        btn_lay.addWidget(self.btn_clear)
        left_layout.addLayout(btn_lay)
        
        left_layout.addStretch()
        main_layout.addWidget(left_widget)
        
        # --- RIGHT PANEL: Console Log ---
        self.txt_console = QPlainTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet(
            "background-color: black;"
            "color: #39FF14;"
            "font-family: 'Consolas', 'Courier New', monospace;"
            "font-size: 10pt;"
        )
        main_layout.addWidget(self.txt_console)

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.setText("Resume" if self.is_paused else "Pause")

    def _clear_log(self):
        self.txt_console.clear()
        self.line_counter = 1

    def _on_status_changed(self, connected, msg):
        if connected:
            self.lbl_status.setText("Connected")
            self.lbl_status.setStyleSheet("font-weight: bold; color: green; font-size: 11pt;")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        else:
            # If reconnect is enabled, show Reconnecting status
            if self.chk_reconnect.isChecked() and self.reader._running:
                self.lbl_status.setText("Reconnecting...")
                self.lbl_status.setStyleSheet("font-weight: bold; color: orange; font-size: 11pt;")
                self.btn_connect.setEnabled(False)
                self.btn_disconnect.setEnabled(True)
            else:
                self.lbl_status.setText("Disconnected")
                self.lbl_status.setStyleSheet("font-weight: bold; color: red; font-size: 11pt;")
                self.btn_connect.setEnabled(True)
                self.btn_disconnect.setEnabled(False)
                
            # Print disconnect error in console (if not paused)
            if not self.is_paused and msg:
                self._append_console_text(f"\n[SYSTEM ERROR: {msg}]\n")

    def _on_data_received(self, data):
        if self.is_paused:
            return
            
        self.byte_buffer.extend(data)
        
        eol_type = self.combo_eol.currentData()
        display_mode = self.combo_mode.currentText()
        
        if eol_type == "none":
            # No custom EOL: print as much as possible immediately
            if display_mode == "ASCII":
                # Decode string, replacing decode errors to avoid crash
                text = self.byte_buffer.decode('utf-8', errors='replace')
                self.byte_buffer.clear()
                self._append_console_text(text)
            else:
                hex_str = " ".join(f"{b:02X}" for b in self.byte_buffer) + " "
                self.byte_buffer.clear()
                self._append_console_text(hex_str)
        else:
            # We have a custom EOL sequence
            eol_bytes = eol_type
            while eol_bytes in self.byte_buffer:
                idx = self.byte_buffer.index(eol_bytes)
                line_bytes = self.byte_buffer[:idx]
                del self.byte_buffer[:idx + len(eol_bytes)]
                
                self._print_line(line_bytes, display_mode)

    def _print_line(self, line_bytes, display_mode):
        if display_mode == "ASCII":
            line_text = line_bytes.decode('utf-8', errors='replace')
        else:
            line_text = " ".join(f"{b:02X}" for b in line_bytes)
            
        prefix = ""
        if self.chk_line_nums.isChecked():
            prefix += f"[{self.line_counter:04d}] "
            self.line_counter += 1
            
        if self.chk_timestamps.isChecked():
            dt = datetime.now()
            time_part = dt.strftime('%d-%b-%Y %I:%M:%S')
            ms_part = f"{dt.microsecond // 1000:03d}"
            ampm = dt.strftime('%p')
            prefix += f"[{time_part}.{ms_part} {ampm}] "
            
        self._append_console_text(f"{prefix}{line_text}\n")

    def _append_console_text(self, text):
        self.txt_console.insertPlainText(text)
        
        # Limit line count to prevent infinite memory usage
        doc = self.txt_console.document()
        if doc.characterCount() > 50000:
            cursor = self.txt_console.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 100)
            cursor.removeSelectedText()
            
        if self.chk_scroll.isChecked():
            self.txt_console.ensureCursorVisible()

    def _restart_connection(self):
        if self.reader.isRunning():
            self.reader._running = False
            self.reader.wait()
            
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
            
        # Parse connection configurations
        self.reader.baud_rate = self.combo_baud.currentData()
        self.reader.bytesize = self.combo_data.currentData()
        self.reader.parity = self.combo_parity.currentData()
        self.reader.stopbits = self.combo_stop.currentData()
        
        flow = self.combo_flow.currentData()
        self.reader.xonxoff = flow in ("xonxoff", "combined")
        self.reader.rtscts = flow in ("rtscts", "combined")
        
        self.reader.dtr_state = self.chk_dtr.isChecked()
        self.reader.rts_state = self.chk_rts.isChecked()
        
        self.reader.poll_interval_ms = int(self.txt_poll.text()) if (self.chk_poll.isChecked() and self.txt_poll.text()) else 0
        self.reader.reconnect_enabled = self.chk_reconnect.isChecked()
        self.reader.reconnect_interval_ms = int(self.txt_reconnect.text()) if self.txt_reconnect.text() else 1000
        
        self.reader.start()

    def _disconnect_port(self):
        """Cleanly stops connection loop and releases COM port."""
        if self.reader.isRunning():
            self.reader._running = False
            self.reader.wait()
            
        self.lbl_status.setText("Disconnected")
        self.lbl_status.setStyleSheet("font-weight: bold; color: red; font-size: 11pt;")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    def _load_settings(self):
        """Loads and applies stored configuration settings for this COM port."""
        # Temporarily block widget signals to prevent recursive, rapid calls to _restart_connection
        self.combo_baud.blockSignals(True)
        self.combo_data.blockSignals(True)
        self.combo_parity.blockSignals(True)
        self.combo_stop.blockSignals(True)
        self.combo_flow.blockSignals(True)
        self.chk_rts.blockSignals(True)
        self.chk_dtr.blockSignals(True)
        self.chk_poll.blockSignals(True)
        self.txt_poll.blockSignals(True)
        self.chk_reconnect.blockSignals(True)
        self.txt_reconnect.blockSignals(True)
        self.combo_eol.blockSignals(True)
        self.combo_mode.blockSignals(True)
        self.chk_line_nums.blockSignals(True)
        self.chk_timestamps.blockSignals(True)
        self.chk_scroll.blockSignals(True)
        
        try:
            qp_settings = self.config.get("quick_peek_settings", {})
            port_settings = qp_settings.get(self.port_path, {})
            
            def set_combo_by_data(combo, val):
                if val is None: return
                idx = combo.findData(val)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                    
            set_combo_by_data(self.combo_baud, port_settings.get("baud_rate"))
            set_combo_by_data(self.combo_data, port_settings.get("data_bits"))
            set_combo_by_data(self.combo_parity, port_settings.get("parity"))
            set_combo_by_data(self.combo_stop, port_settings.get("stop_bits"))
            set_combo_by_data(self.combo_flow, port_settings.get("flow_control"))
            
            self.chk_rts.setChecked(port_settings.get("rts_on", False))
            self.chk_dtr.setChecked(port_settings.get("dtr_on", False))
            
            self.chk_poll.setChecked(port_settings.get("poll_enabled", True))
            self.txt_poll.setText(str(port_settings.get("poll_interval", "100")))
            
            self.chk_reconnect.setChecked(port_settings.get("reconnect_enabled", True))
            self.txt_reconnect.setText(str(port_settings.get("reconnect_interval", "1000")))
            
            eol_idx = port_settings.get("rx_eol_index")
            if eol_idx is not None and 0 <= eol_idx < self.combo_eol.count():
                self.combo_eol.setCurrentIndex(eol_idx)
                
            mode = port_settings.get("display_mode")
            if mode:
                self.combo_mode.setCurrentText(mode)
                
            self.chk_line_nums.setChecked(port_settings.get("show_line_num", False))
            self.chk_timestamps.setChecked(port_settings.get("show_timestamp", False))
            self.chk_scroll.setChecked(port_settings.get("auto_scroll", True))
        finally:
            # Restore widget signals
            self.combo_baud.blockSignals(False)
            self.combo_data.blockSignals(False)
            self.combo_parity.blockSignals(False)
            self.combo_stop.blockSignals(False)
            self.combo_flow.blockSignals(False)
            self.chk_rts.blockSignals(False)
            self.chk_dtr.blockSignals(False)
            self.chk_poll.blockSignals(False)
            self.txt_poll.blockSignals(False)
            self.chk_reconnect.blockSignals(False)
            self.txt_reconnect.blockSignals(False)
            self.combo_eol.blockSignals(False)
            self.combo_mode.blockSignals(False)
            self.chk_line_nums.blockSignals(False)
            self.chk_timestamps.blockSignals(False)
            self.chk_scroll.blockSignals(False)

    def _save_settings(self):
        """Saves current configuration settings for this COM port to config."""
        qp_settings = self.config.get("quick_peek_settings", {})
        qp_settings[self.port_path] = {
            "baud_rate": self.combo_baud.currentData(),
            "data_bits": self.combo_data.currentData(),
            "parity": self.combo_parity.currentData(),
            "stop_bits": self.combo_stop.currentData(),
            "flow_control": self.combo_flow.currentData(),
            "rts_on": self.chk_rts.isChecked(),
            "dtr_on": self.chk_dtr.isChecked(),
            "poll_enabled": self.chk_poll.isChecked(),
            "poll_interval": self.txt_poll.text(),
            "reconnect_enabled": self.chk_reconnect.isChecked(),
            "reconnect_interval": self.txt_reconnect.text(),
            "rx_eol_index": self.combo_eol.currentIndex(),
            "display_mode": self.combo_mode.currentText(),
            "show_line_num": self.chk_line_nums.isChecked(),
            "show_timestamp": self.chk_timestamps.isChecked(),
            "auto_scroll": self.chk_scroll.isChecked()
        }
        self.config.set("quick_peek_settings", qp_settings)
        self.config.save_config()

    def closeEvent(self, event):
        # Save settings first
        try:
            self._save_settings()
        except Exception:
            pass
            
        # Signal thread loop to terminate
        self.reader._running = False
        
        # Close serial port from the main GUI thread to break any blocking read() calls
        if self.reader.ser:
            try:
                self.reader.ser.close()
            except Exception:
                pass
                
        # Do not block here. We emit closed_signal so the parent removes this window from active peeks.
        # Once the thread finishes running, deleteLater() will reclaim memory safely.
        self.closed_signal.emit()
        event.accept()
