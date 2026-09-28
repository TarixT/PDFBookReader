import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pdf_audiobook.audio.renderer import run_job, JobControl, Cancelled
from pdf_audiobook.tts.test_tone import TestToneBackend as ToneBackend

SETTINGS = {"backend": "test-tone", "device": 0, "chunk_size": 80, "pause_ms": 20, "format": "wav", "reference": "", "generation": {}}


class PipelineTests(unittest.TestCase):
    def test_resume_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_job("", tmp, SETTINGS, sample=True)
            self.assertTrue(json.loads(manifest.read_text())["completed_chapters"])
            with patch.object(ToneBackend, "generate", side_effect=AssertionError("must reuse")):
                run_job("", tmp, SETTINGS, sample=True)
            chunk = next((Path(tmp)/"chunks").glob("*.wav"))
            chunk.write_bytes(b"broken")
            run_job("", tmp, SETTINGS, sample=True)
            self.assertGreater(chunk.stat().st_size, 44)
            original = manifest.read_bytes()
            changed_settings = {**SETTINGS, "chunk_size": 90}
            changed = run_job("", tmp, changed_settings, sample=True)
            self.assertNotEqual(changed.parent, manifest.parent)
            self.assertEqual(manifest.read_bytes(), original)
            with patch.object(ToneBackend, "generate", side_effect=AssertionError("must reuse")):
                self.assertEqual(run_job("", tmp, changed_settings, sample=True), changed)

    def test_cancel_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            control = JobControl()
            def report(stage, done, total):
                if stage.startswith("Audio generation"):
                    control.cancel()
            with self.assertRaises(Cancelled):
                run_job("", tmp, SETTINGS, report, control, sample=True)
            self.assertEqual(len(json.loads((Path(tmp)/"project.json").read_text())["chunks"]), 1)
            run_job("", tmp, SETTINGS, sample=True)

    def test_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = ToneBackend.generate
            calls = []
            def fail_second(backend, *args, **kwargs):
                calls.append(1)
                if len(calls) == 2:
                    raise RuntimeError("simulated failure")
                return original(backend, *args, **kwargs)
            with patch.object(ToneBackend, "generate", fail_second):
                with self.assertRaisesRegex(RuntimeError, "simulated"):
                    run_job("", tmp, SETTINGS, sample=True)
            self.assertEqual(len(json.loads((Path(tmp)/"project.json").read_text())["chunks"]), 1)
            run_job("", tmp, SETTINGS, sample=True)

    def test_pdf(self):
        import pymupdf
        from pdf_audiobook.pdf.parser import parse_pdf
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"book.pdf"
            with pymupdf.open() as doc:
                for text in ("Chapter One\nA quiet morning.", "Chapter Two\nAn exciting evening."):
                    doc.new_page().insert_text((72, 72), text)
                doc.set_metadata({"title": "Test Book"})
                doc.save(path)
            book = parse_pdf(str(path))
            self.assertEqual(book.title, "Test Book")
            self.assertEqual(len(book.chapters), 2)
            run_job(str(path), str(Path(tmp)/"audio"), SETTINGS)
            self.assertEqual(len(list((Path(tmp)/"audio").glob("*.wav"))), 2)
