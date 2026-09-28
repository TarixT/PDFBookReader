from .chatterbox_turbo import ChatterboxTurboBackend
from .test_tone import TestToneBackend
from .kokoro import KokoroBackend

TTS_REGISTRY = {"kokoro": KokoroBackend, "chatterbox-turbo": ChatterboxTurboBackend, "test-tone": TestToneBackend}
