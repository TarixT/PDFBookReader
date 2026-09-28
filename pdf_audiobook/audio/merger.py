import math
import shutil
import subprocess
from pathlib import Path


def valid_audio(path: Path) -> bool:
    try:
        import soundfile as sf
        with sf.SoundFile(path) as audio:
            return len(audio) > 0 and audio.samplerate > 0
    except (OSError, RuntimeError):
        return False


def merge_audio(paths: list[Path], destination: Path, pause_ms: int = 80,
                checkpoint=lambda: None):
    """Stream chapter chunks, resample to the first rate, and export atomically."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    if destination.suffix == ".mp3" and not shutil.which("ffmpeg"):
        raise RuntimeError("MP3 export needs FFmpeg on PATH. Install it or start a WAV project.")
    wav = destination.with_suffix(".assembling.wav")
    rate = sf.info(paths[0]).samplerate
    try:
        with sf.SoundFile(wav, "w", samplerate=rate, channels=1, subtype="PCM_16") as output:
            for index, path in enumerate(paths):
                checkpoint()
                data, source_rate = sf.read(path, dtype="float32", always_2d=True)
                data = data.mean(axis=1)
                if source_rate != rate:
                    divisor = math.gcd(source_rate, rate)
                    data = resample_poly(data, rate//divisor, source_rate//divisor)
                if not np.isfinite(data).all():
                    raise ValueError(f"Invalid samples in {path.name}")
                peak = float(np.max(np.abs(data))) if len(data) else 0
                if peak > .99:
                    data *= .99 / peak
                fade = min(int(rate*.005), len(data)//2)
                if fade:
                    data[:fade] *= np.linspace(0, 1, fade)
                    data[-fade:] *= np.linspace(1, 0, fade)
                output.write(data)
                if index < len(paths)-1 and pause_ms:
                    output.write(np.zeros(int(rate*pause_ms/1000), dtype="float32"))
        checkpoint()
        if destination.suffix == ".mp3":
            temporary = destination.with_suffix(".encoding.mp3")
            process = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "2", str(temporary)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                while True:
                    try:
                        code = process.wait(timeout=.2)
                        break
                    except subprocess.TimeoutExpired:
                        checkpoint()
                if code:
                    raise RuntimeError("FFmpeg encoding failed. Verify the encoder and available disk space.")
                temporary.replace(destination)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                temporary.unlink(missing_ok=True)
        else:
            wav.replace(destination)
    finally:
        wav.unlink(missing_ok=True)
