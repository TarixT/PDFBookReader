from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton, QFileDialog
from pdf_audiobook.tts.registry import TTS_REGISTRY


class SettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.form = QFormLayout(self)
        self.backend = QComboBox()
        for key, cls in TTS_REGISTRY.items():
            self.backend.addItem(cls.label, key)
        self.device = QSpinBox()
        self.device.setRange(0, 31)
        self.chunk = QSpinBox()
        self.chunk.setRange(20, 2000)
        self.chunk.setValue(500)
        self.pause = QSpinBox()
        self.pause.setRange(0, 2000)
        self.pause.setValue(80)
        self.format = QComboBox()
        self.format.addItems(["wav", "mp3"])
        self.reference = QLineEdit()
        self.browse = QPushButton("Choose reference WAV (optional)")
        self.browse.clicked.connect(self.choose_reference)
        for title, widget in [("Model", self.backend), ("CUDA device", self.device), ("Chunk characters", self.chunk), ("Pause between chunks (ms)", self.pause), ("Output format", self.format), ("Reference audio", self.reference), ("", self.browse)]:
            self.form.addRow(title, widget)
        self.options_widget = QWidget()
        self.options_form = QFormLayout(self.options_widget)
        self.form.addRow(self.options_widget)
        self.options = {}
        self.backend.currentIndexChanged.connect(self.update_options)
        self.update_options()

    def update_options(self):
        while self.options_form.rowCount():
            self.options_form.removeRow(0)
        self.options = {}
        backend = TTS_REGISTRY[self.backend.currentData()](self.device.value())
        self.chunk.setMaximum(backend.get_max_text_length())
        self.reference.setEnabled(backend.supports_voice_cloning())
        self.browse.setEnabled(backend.supports_voice_cloning())
        for name, choices in backend.choices.items():
            widget = QComboBox()
            for value, label in choices.items():
                widget.addItem(label, value)
            self.options[name] = widget
            self.options_form.addRow(name.capitalize(), widget)
        for name, (default, low, high) in backend.options.items():
            widget = QDoubleSpinBox()
            widget.setRange(low, high)
            widget.setValue(default)
            widget.setSingleStep(.05 if high < 10 else 1)
            self.options[name] = widget
            self.options_form.addRow(name.replace("_", " ").capitalize(), widget)

    def choose_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Reference audio", "", "Audio (*.wav *.flac)")
        if path:
            self.reference.setText(path)

    def values(self):
        return {"backend": self.backend.currentData(), "device": self.device.value(), "chunk_size": self.chunk.value(), "pause_ms": self.pause.value(), "format": self.format.currentText(), "reference": self.reference.text().strip() if self.reference.isEnabled() else "", "generation": {name: widget.currentData() if isinstance(widget, QComboBox) else widget.value() for name, widget in self.options.items()}}

    def restore(self, values):
        index = self.backend.findData(values.get("backend"))
        if index >= 0:
            self.backend.setCurrentIndex(index)
        self.device.setValue(values.get("device", 0))
        self.chunk.setValue(values.get("chunk_size", 500))
        self.pause.setValue(values.get("pause_ms", 80))
        self.format.setCurrentText(values.get("format", "wav"))
        self.reference.setText(values.get("reference", ""))
        for name, value in values.get("generation", {}).items():
            if name in self.options:
                widget = self.options[name]
                if isinstance(widget, QComboBox):
                    widget.setCurrentIndex(max(0, widget.findData(value)))
                else:
                    widget.setValue(value)
