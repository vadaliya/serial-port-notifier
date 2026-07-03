from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QFormLayout)
from PyQt6.QtCore import Qt

class EditLauncherDialog(QDialog):
    def __init__(self, launcher_data=None):
        super().__init__()
        self.setWindowTitle("Edit Launcher")
        self.setMinimumWidth(400)
        
        # If editing, use existing data. If new, start empty.
        self.data = launcher_data or {"label": "", "program": "", "args": "-serial %1"}
        
        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Label Input
        self.txt_label = QLineEdit(self.data.get("label", ""))
        form_layout.addRow("Label:", self.txt_label)

        # Program Input with Browse Button
        prog_layout = QHBoxLayout()
        self.txt_program = QLineEdit(self.data.get("program", ""))
        self.txt_program.textChanged.connect(self._update_preview)
        
        self.btn_browse = QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self._browse_file)
        
        prog_layout.addWidget(self.txt_program)
        prog_layout.addWidget(self.btn_browse)
        form_layout.addRow("Program:", prog_layout)

        # Command Line Arguments
        self.txt_args = QLineEdit(self.data.get("args", ""))
        self.txt_args.textChanged.connect(self._update_preview)
        form_layout.addRow("Command Line:", self.txt_args)
        
        layout.addLayout(form_layout)

        # Preview & Help Text
        self.lbl_preview = QLabel("Preview: ")
        self.lbl_preview.setStyleSheet("color: gray; margin-top: 5px;")
        layout.addWidget(self.lbl_preview)
        
        help_text = QLabel("Command Line Options:\n%1 - COM port name (e.g. COM15)\n%2 - COM port number (e.g. 15)")
        help_text.setStyleSheet("color: gray;")
        layout.addWidget(help_text)

        # Buttons (OK/Cancel)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Program", "", "Executables (*.exe);;All Files (*)")
        if file_path:
            self.txt_program.setText(file_path)

    def _update_preview(self):
        prog = self.txt_program.text().split('/')[-1].split('\\')[-1] # Get just the filename
        args = self.txt_args.text().replace("%1", "COM15").replace("%2", "15")
        self.lbl_preview.setText(f"Preview: {prog} {args}")

    def get_data(self):
        """Returns the updated dictionary when OK is clicked."""
        return {
            "id": self.data.get("id", f"launcher_{hash(self.txt_label.text())}"), # simple ID generation
            "label": self.txt_label.text(),
            "program": self.txt_program.text(),
            "args": self.txt_args.text()
        }