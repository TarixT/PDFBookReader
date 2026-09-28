import json
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox, QTabWidget, QCheckBox
from pdf_audiobook.models import Book
from pdf_audiobook.utils.config import CONFIG_PATH, load_config, save_json
from .settings_panel import SettingsPanel
from .progress_panel import ProgressPanel
from .worker import Worker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Audiobook — local CUDA narration")
        self.resize(850, 850)
        self.worker = None
        container = QWidget()
        layout = QVBoxLayout(container)
        self.setCentralWidget(container)
        self.inputs = QWidget()
        inputs = QVBoxLayout(self.inputs)
        self.source, self.output = QLineEdit(), QLineEdit()
        for label, edit, callback in [("Select PDF", self.source, self.choose_pdf), ("Output directory", self.output, self.choose_output)]:
            row = QHBoxLayout()
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
            row.addWidget(edit)
            inputs.addLayout(row)
        self.sample = QCheckBox("Sample mode: narrate two built-in paragraphs (PDF not required)")
        inputs.addWidget(self.sample)
        self.info = QLabel("Load a PDF to inspect its title, pages and chapters.")
        self.info.setWordWrap(True)
        inputs.addWidget(self.info)
        tabs = QTabWidget()
        self.settings = SettingsPanel()
        tabs.addTab(self.settings, "Narration settings")
        training = QLabel("Training / fine-tuning is an extension point only.\nNo training workflow is implemented. Normal narration needs no training.\nSee training/base.py to integrate a separately validated workflow.")
        training.setWordWrap(True)
        tabs.addTab(training, "Training / Fine-tuning (experimental)")
        inputs.addWidget(tabs)
        layout.addWidget(self.inputs)
        buttons = QHBoxLayout()
        self.start = QPushButton("Start / continue")
        self.resume = QPushButton("Resume project…")
        self.pause = QPushButton("Pause")
        self.cancel = QPushButton("Cancel")
        for button in (self.start, self.resume, self.pause, self.cancel):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.progress = ProgressPanel()
        layout.addWidget(self.progress)
        self.start.clicked.connect(self.start_job)
        self.resume.clicked.connect(self.resume_project)
        self.pause.clicked.connect(self.toggle_pause)
        self.cancel.clicked.connect(self.cancel_job)
        config = load_config()
        self.settings.restore(config.get("settings", {}))
        self.output.setText(config.get("output", ""))
        self.busy(False)

    def busy(self, value):
        self.inputs.setEnabled(not value)
        self.start.setEnabled(not value)
        self.resume.setEnabled(not value)
        self.pause.setEnabled(value)
        self.cancel.setEnabled(value)
        self.pause.setText("Pause")

    def choose_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF (*.pdf)")
        if path:
            self.source.setText(path)
            self.launch(Worker(path, inspect=True))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a project output directory")
        if path:
            self.output.setText(path)

    def launch(self, worker):
        self.worker = worker
        self.busy(True)
        worker.progress.connect(self.on_progress)
        worker.message.connect(self.progress.logs.appendPlainText)
        worker.error.connect(self.show_error)
        worker.result.connect(self.on_result)
        worker.finished.connect(self.on_finished)
        worker.start()

    def on_progress(self, stage, done, total):
        if stage.startswith("Output directory: "):
            self.output.setText(stage.removeprefix("Output directory: "))
        self.progress.update_progress(stage, done, total)

    def start_job(self):
        if not self.output.text().strip() or (not self.sample.isChecked() and not self.source.text().strip()):
            self.show_error("Choose an output directory and a PDF, or enable sample mode.")
            return
        settings = self.settings.values()
        try:
            save_json(CONFIG_PATH, {"settings": settings, "output": self.output.text().strip()})
        except OSError as exc:
            self.progress.logs.appendPlainText(f"Could not save preferences: {exc}")
        self.launch(Worker(self.source.text().strip(), self.output.text().strip(), settings, self.sample.isChecked()))

    def resume_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Resume project", "", "Project (project.json)")
        if not path:
            return
        try:
            state = json.loads(Path(path).read_text(encoding="utf-8"))
            self.settings.restore(state["identity"]["settings"])
            self.source.setText(state["book"]["source"])
            self.output.setText(str(Path(path).parent))
            self.sample.setChecked(state.get("sample", False))
            self.start_job()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.show_error(f"Unable to open project: {exc}")

    def toggle_pause(self):
        if self.worker.control.running.is_set():
            self.worker.control.running.clear()
            self.pause.setText("Continue")
            self.progress.logs.appendPlainText("Pause requested; takes effect after the current operation.")
        else:
            self.worker.control.running.set()
            self.pause.setText("Pause")

    def cancel_job(self):
        self.worker.control.cancel()
        self.progress.logs.appendPlainText("Cancellation requested; waiting for the current operation to finish.")
        self.pause.setEnabled(False)
        self.cancel.setEnabled(False)

    def on_result(self, result):
        if isinstance(result, Book):
            titles = ", ".join(c.title for c in result.chapters[:12])
            self.info.setText(f"{result.title} | {result.page_count} pages | {len(result.chapters)} chapters\n{titles}")
        else:
            self.progress.logs.appendPlainText(f"Completed. Project saved: {result}")
        self.progress.status.setText("Complete")

    def show_error(self, message):
        self.progress.status.setText("Error")
        self.progress.logs.appendPlainText(message)
        QMessageBox.critical(self, "PDF Audiobook", message)

    def on_finished(self):
        self.busy(False)
        if self.worker.control.cancelled.is_set():
            self.progress.status.setText("Cancelled — saved progress can be resumed")
        self.worker.deleteLater()
        self.worker = None

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel_job()
            self.progress.logs.appendPlainText("Please close again after the worker stops.")
            event.ignore()
        else:
            event.accept()
