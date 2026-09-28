import argparse
import logging


def main():
    parser = argparse.ArgumentParser(description="PDF audiobook desktop application")
    parser.add_argument("--smoke-test", metavar="OUTPUT", help="Render diagnostic sample tones without CUDA or GUI")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.smoke_test:
        from .audio.renderer import run_job
        run_job("", args.smoke_test, {"backend": "test-tone", "device": 0, "chunk_size": 100, "pause_ms": 80, "format": "wav", "reference": "", "generation": {}},
                lambda stage, done, total: logging.info("%s: %s/%s", stage, done, total), sample=True)
        return
    try:
        from PySide6.QtWidgets import QApplication
        from .gui.main_window import MainWindow
    except ImportError as exc:
        parser.exit(1, f"Missing desktop dependency: {exc}. Install requirements.txt.\n")
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
