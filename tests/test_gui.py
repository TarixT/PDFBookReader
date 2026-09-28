import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from pdf_audiobook.gui.main_window import MainWindow
from pdf_audiobook.gui.worker import Worker


class GuiTests(unittest.TestCase):
    def test_window_and_background_sample(self):
        app = QApplication.instance() or QApplication([])
        with patch("pdf_audiobook.gui.main_window.load_config", return_value={}):
            window = MainWindow()
        window.settings.backend.setCurrentIndex(window.settings.backend.findData("kokoro"))
        values = window.settings.values()
        self.assertEqual(values["generation"]["voice"], "am_michael")
        window.settings.restore(values)
        self.assertEqual(window.settings.values(), values)
        window.settings.backend.setCurrentIndex(window.settings.backend.findData("test-tone"))
        self.assertFalse(window.settings.reference.isEnabled())
        errors = []
        with tempfile.TemporaryDirectory() as tmp:
            worker = Worker("", tmp, window.settings.values(), sample=True)
            worker.error.connect(errors.append)
            window.launch(worker)
            try:
                deadline = time.monotonic() + 15
                while window.worker is not None and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                self.assertIsNone(window.worker)
                self.assertFalse(errors)
                self.assertTrue(window.start.isEnabled())
                self.assertTrue((Path(tmp)/"project.json").exists())
            finally:
                if window.worker:
                    window.worker.control.cancel()
                    window.worker.wait(10000)
                window.close()
