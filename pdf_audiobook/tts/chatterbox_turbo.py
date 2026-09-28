import gc
from pathlib import Path
from .base import TTSBackend
from pdf_audiobook.hardware.cuda_manager import CudaManager


class ChatterboxTurboBackend(TTSBackend):
    label = "Chatterbox Turbo (CUDA)"
    options = {"temperature": (.8, .1, 2.0), "top_p": (.95, .01, 1.0),
               "repetition_penalty": (1.2, 1.0, 3.0), "top_k": (1000, 1, 2000)}

    def __init__(self, device=0):
        super().__init__(device)
        self.cuda = CudaManager(device)
        self.model = None
        self.reference = None

    def load(self):
        self.cuda.require()
        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS
        except ImportError as exc:
            raise RuntimeError("Chatterbox Turbo is missing; follow README optional backend installation.") from exc
        self.model = ChatterboxTurboTTS.from_pretrained(device=self.cuda.device)

    def unload(self):
        self.model = None
        gc.collect()
        try:
            self.cuda.clear()
        except ImportError:
            pass

    def generate(self, text: str, output_path: Path, **kwargs):
        import soundfile as sf
        torch = self.cuda.require()
        reference = kwargs.pop("reference", "")
        kwargs.pop("mixed_precision", None)  # Full precision: external autocast is unverified for Turbo.
        if reference and reference != self.reference:
            info = sf.info(reference)
            if info.duration <= 5:
                raise ValueError("Reference audio must be longer than 5 seconds; use a clean WAV recording.")
            self.model.prepare_conditionals(reference)
            self.reference = reference
        if "top_k" in kwargs:
            kwargs["top_k"] = int(kwargs["top_k"])
        try:
            with torch.inference_mode():
                audio = self.model.generate(text, **kwargs)
            sf.write(str(output_path), audio.detach().cpu().numpy().reshape(-1), self.model.sr, subtype="PCM_16")
        except torch.cuda.OutOfMemoryError as exc:
            raise RuntimeError("GPU out of memory. Close other GPU applications, then resume; use smaller chunks in a new project if needed.") from exc

    def get_max_text_length(self):
        return 500  # Conservative application policy, not a claimed upstream token limit.

    def supports_voice_cloning(self):
        return True

    def status(self):
        return self.cuda.describe()
