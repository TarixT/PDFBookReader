from abc import ABC, abstractmethod
from pathlib import Path


class TTSBackend(ABC):
    """One instance owned by one job; generate lossless mono WAV files."""
    label = "Backend"
    options: dict[str, tuple[float, float, float]] = {}
    choices: dict[str, dict[str, str]] = {}

    def __init__(self, device: int = 0):
        self.device = device

    @abstractmethod
    def load(self): ...

    @abstractmethod
    def unload(self): ...

    @abstractmethod
    def generate(self, text: str, output_path: Path, **kwargs): ...

    @abstractmethod
    def get_max_text_length(self) -> int: ...

    def supports_voice_cloning(self) -> bool:
        return False

    def status(self) -> str:
        return self.label
