from .base import TTSBackend


class TestToneBackend(TTSBackend):
    """Explicit diagnostic backend. Produces tones, never speech."""
    label = "Test tone (no speech / no GPU)"

    def load(self): pass
    def unload(self): pass
    def get_max_text_length(self): return 2000

    def generate(self, text, output_path, **kwargs):
        import numpy as np
        import soundfile as sf
        rate = 24000
        t = np.arange(int(rate * min(2, max(.2, len(text)/100)))) / rate
        sf.write(str(output_path), .1 * np.sin(2*np.pi*440*t) * np.minimum(1, t*50) * np.minimum(1, (t[-1]-t)*50), rate)
