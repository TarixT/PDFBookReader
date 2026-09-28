import logging
from PySide6.QtCore import QThread, Signal
from pdf_audiobook.audio.renderer import run_job, Cancelled, JobControl
from pdf_audiobook.pdf.parser import parse_pdf


class SignalHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        self.signal.emit(self.format(record))


class Worker(QThread):
    progress = Signal(str, int, int)
    message = Signal(str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, source, output="", settings=None, sample=False, inspect=False):
        super().__init__()
        self.args = source, output, settings, sample, inspect
        self.control = JobControl()

    def run(self):
        handler = SignalHandler(self.message)
        logging.getLogger().addHandler(handler)
        source, output, settings, sample, inspect = self.args
        try:
            if inspect:
                value = parse_pdf(source, self.progress.emit, self.control.checkpoint)
            else:
                value = run_job(source, output, settings, self.progress.emit, self.control, sample)
            self.result.emit(value)
        except Cancelled:
            self.message.emit("Cancelled. Completed chunks are saved; resume with the same project settings.")
        except Exception as exc:
            logging.getLogger(__name__).exception("Job failed")
            self.error.emit(str(exc))
        finally:
            logging.getLogger().removeHandler(handler)
