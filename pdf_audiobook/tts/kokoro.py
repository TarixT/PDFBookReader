"""Optional Kokoro backend with American English male narration."""
import gc
from pathlib import Path
from .base import TTSBackend
from pdf_audiobook.hardware.cuda_manager import CudaManager


class KokoroBackend(TTSBackend):
    label = "Kokoro — Michael (CUDA)"
    options = {"speed": (1.0, .5, 2.0)}
    choices = {"voice": {"am_michael": "Michael — American male"}}

    def __init__(self, device: int = 0):
        super().__init__(device)
        self.cuda = CudaManager(device)
        self.pipeline = None

    def load(self):
        self.cuda.require()
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise RuntimeError("Install requirements-kokoro.txt to use the Michael voice.") from exc
        self.pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device=self.cuda.device)

    def generate(self, text: str, output_path: Path, **kwargs):
        import numpy as np
        import soundfile as sf
        if self.pipeline is None:
            raise RuntimeError("Kokoro has not been loaded.")
        voice = kwargs.get("voice", "am_michael")
        speed = float(kwargs.get("speed", 1.0))
        if voice not in self.choices["voice"] or not .5 <= speed <= 2:
            raise ValueError("Invalid Kokoro voice or speed.")
        torch = self.cuda.require()
        frames = 0
        try:
            with torch.inference_mode(), sf.SoundFile(output_path, "w", samplerate=24000,
                                                      channels=1, subtype="PCM_16") as output:
                # Kokoro may split input further; retain every returned segment.
                for _, _, audio in self.pipeline(text, voice=voice, speed=speed):
                    if audio is None:
                        raise RuntimeError("Kokoro returned no audio for a segment.")
                    samples = audio.detach().cpu().numpy().reshape(-1)
                    if not np.isfinite(samples).all():
                        raise RuntimeError("Kokoro returned invalid audio samples.")
                    output.write(np.clip(samples, -.99, .99))
                    frames += len(samples)
            if not frames:
                raise RuntimeError("Kokoro produced no speech for this text.")
        except torch.cuda.OutOfMemoryError as exc:
            raise RuntimeError("Kokoro ran out of GPU memory. Close other GPU applications and resume.") from exc

    def unload(self):
        self.pipeline = None
        gc.collect()
        try:
            self.cuda.clear()
        except ImportError:
            pass

    def get_max_text_length(self) -> int:
        return 500

    def status(self) -> str:
        return self.cuda.describe()
