import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from contextlib import nullcontext
import numpy as np
import soundfile as sf
from pdf_audiobook.tts.kokoro import KokoroBackend


class KokoroTests(unittest.TestCase):
    def test_all_segments_and_michael_default(self):
        backend = KokoroBackend()
        backend.cuda = MagicMock()
        backend.cuda.require.return_value.inference_mode.return_value = nullcontext()
        backend.cuda.require.return_value.cuda.OutOfMemoryError = MemoryError
        audio = MagicMock()
        audio.detach.return_value.cpu.return_value.numpy.return_value = np.ones(2400) * .1
        backend.pipeline = MagicMock(return_value=iter([("one", "", audio), ("two", "", audio)]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"sample.wav"
            backend.generate("Some text", path)
            self.assertEqual(sf.info(path).frames, 4800)
            self.assertEqual(sf.info(path).samplerate, 24000)
        backend.pipeline.assert_called_once_with("Some text", voice="am_michael", speed=1.0)
