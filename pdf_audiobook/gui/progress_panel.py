from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPlainTextEdit


class ProgressPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.status = QLabel("Ready")
        self.bar = QProgressBar()
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(3000)
        for widget in (self.status, self.bar, self.logs):
            layout.addWidget(widget)

    def update_progress(self, stage, done, total):
        self.status.setText(stage)
        self.bar.setRange(0, max(total, 1))
        self.bar.setValue(done)
        self.logs.appendPlainText(f"{stage}: {done}/{total}")
