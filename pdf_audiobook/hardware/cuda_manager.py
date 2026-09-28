from contextlib import nullcontext


class CudaManager:
    """Single gateway to CUDA; never substitute CPU inference."""
    def __init__(self, index: int = 0):
        self.index = index
        self.device = f"cuda:{index}"

    def require(self):
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("Install CUDA-enabled PyTorch and the optional TTS dependencies.") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable. An NVIDIA GPU, driver and CUDA-enabled PyTorch are required.")
        if not 0 <= self.index < torch.cuda.device_count():
            raise ValueError(f"CUDA device {self.index} does not exist.")
        torch.cuda.set_device(self.index)
        return torch

    def describe(self) -> str:
        torch = self.require()
        free, total = torch.cuda.mem_get_info(self.index)
        return f"{torch.cuda.get_device_name(self.index)} | VRAM {(total-free)/2**30:.1f}/{total/2**30:.1f} GiB used"

    def autocast(self, enabled: bool = False):
        torch = self.require()
        return torch.autocast("cuda", dtype=torch.float16) if enabled else nullcontext()

    def clear(self):
        import torch
        if torch.cuda.is_available() and 0 <= self.index < torch.cuda.device_count():
            with torch.cuda.device(self.index):
                torch.cuda.empty_cache()
