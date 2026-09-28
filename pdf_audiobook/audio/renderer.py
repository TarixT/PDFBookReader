import json
import hashlib
import logging
import threading
from dataclasses import asdict
from pathlib import Path
from pdf_audiobook.models import Book, Chapter, TextChunk
from pdf_audiobook.pdf.parser import parse_pdf
from pdf_audiobook.text.chunker import chunk_text
from pdf_audiobook.tts.registry import TTS_REGISTRY
from pdf_audiobook.utils.config import save_json
from pdf_audiobook.utils.paths import file_hash, safe_name
from .merger import merge_audio, valid_audio

SAMPLE_TEXT = "A small library stood beside the river. Every evening, its windows glowed with warm light.\n\nOne day a reader discovered a forgotten book. Its pages described a journey across mountains and oceans."
log = logging.getLogger(__name__)
JOB_LOCK = threading.Lock()


class Cancelled(Exception): pass


class JobControl:
    def __init__(self):
        self.cancelled = threading.Event()
        self.running = threading.Event()
        self.running.set()

    def checkpoint(self):
        while not self.running.wait(.1):
            if self.cancelled.is_set():
                raise Cancelled()
        if self.cancelled.is_set():
            raise Cancelled()

    def cancel(self):
        self.cancelled.set()
        self.running.set()


def run_job(source: str, output: str, settings: dict, report=lambda *args: None,
            control: JobControl | None = None, sample: bool = False) -> Path:
    """Sequential generation with validated, durable chunk-level checkpoints."""
    control = control or JobControl()
    if not JOB_LOCK.acquire(blocking=False):
        raise RuntimeError("Another generation job is already running.")
    try:
        return _run(source, output, settings, report, control, sample)
    finally:
        JOB_LOCK.release()


def _run(source, output, settings, report, control, sample):
    directory = Path(output).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # OS lock also prevents separate application instances sharing one project.
    lock_path = directory / ".job.lock"
    with lock_path.open("a+b") as lock:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("This output project is in use by another application instance.") from exc
        return _render(source, directory, settings, report, control, sample)


def _render(source, directory, settings, report, control, sample):
    import shutil
    if settings["format"] == "mp3" and not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required for MP3 export.")
    backend = TTS_REGISTRY[settings["backend"]](settings.get("device", 0))
    limit = min(int(settings["chunk_size"]), backend.get_max_text_length())
    manifest = directory / "project.json"
    reference = settings.get("reference", "")
    identity = {"source_hash": "sample-v1" if sample else file_hash(Path(source)),
                "text_pipeline": 2,
                "settings": settings, "reference_hash": file_hash(Path(reference)) if reference else None}
    if manifest.exists():
        state = json.loads(manifest.read_text(encoding="utf-8"))
        if state.get("identity") != identity or state.get("version") != 1:
            fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            target = directory / f"project-{fingerprint}"
            report("Settings differ from the existing project; using a separate project folder", 0, 1)
            return _run(source, target, settings, report, control, sample)
        chapters = [Chapter(c["title"], c["text"], c["start_page"], [TextChunk(**x) for x in c["chunks"]]) for c in state["book"]["chapters"]]
        book = Book(state["book"]["title"], state["book"]["source"], state["book"]["page_count"], chapters)
        report("Resume", 1, 1)
    else:
        book = Book("Sample book", "", 1, [Chapter("Sample chapter", SAMPLE_TEXT)]) if sample else parse_pdf(source, report, control.checkpoint)
        for i, chapter in enumerate(book.chapters):
            control.checkpoint()
            chapter.chunks = [TextChunk(j, text) for j, text in enumerate(chunk_text(chapter.text, limit))]
            report("Text chunking", i+1, len(book.chapters))
        state = {"version": 1, "identity": identity, "sample": sample, "book": asdict(book), "chunks": {}, "completed_chapters": {}}
        save_json(manifest, state)
    text_directory = directory / "text"
    text_directory.mkdir(exist_ok=True)
    for i, chapter in enumerate(book.chapters, 1):
        (text_directory / f"{i:03d} - {safe_name(chapter.title)}.txt").write_text(chapter.text, encoding="utf-8")
    report(f"Plain-text chapters saved: {text_directory}", 1, 1)
    report(f"Output directory: {directory}", 1, 1)
    report("Book: " + book.title + f" | {book.page_count} pages | {len(book.chapters)} chapters", 1, 1)
    loaded = False
    total = sum(len(ch.chunks) for ch in book.chapters)
    done = 0
    try:
        for i, chapter in enumerate(book.chapters, 1):
            control.checkpoint()
            paths = []
            regenerated = False
            for chunk in chapter.chunks:
                control.checkpoint()
                key = f"{i:03d}-{chunk.index:05d}"
                path = directory / "chunks" / f"{key}.wav"
                paths.append(path)
                entry = state["chunks"].get(key)
                if not (entry and valid_audio(path) and file_hash(path) == entry["sha256"]):
                    regenerated = True
                    state["completed_chapters"].pop(str(i), None)
                    save_json(manifest, state)
                    if not loaded:
                        report("Loading model (first use may download weights)", 0, 1)
                        backend.load()
                        loaded = True
                    report(backend.status(), done, total)
                    path.parent.mkdir(exist_ok=True)
                    temporary = path.with_suffix(".partial.wav")
                    try:
                        backend.generate(chunk.text, temporary, reference=reference, **settings.get("generation", {}))
                        if not valid_audio(temporary):
                            raise RuntimeError("Backend returned empty or invalid audio.")
                        temporary.replace(path)
                    finally:
                        temporary.unlink(missing_ok=True)
                    state["chunks"][key] = {"path": str(path.relative_to(directory)), "sha256": file_hash(path)}
                    save_json(manifest, state)
                done += 1
                report(f"Audio generation | {chapter.title} | chunk {chunk.index+1}/{len(chapter.chunks)}", done, total)
            final = directory / f"{i:03d} - {safe_name(chapter.title)}.{settings['format']}"
            entry = state["completed_chapters"].get(str(i))
            if regenerated or not (entry and final.exists() and file_hash(final) == entry["sha256"]):
                merge_audio(paths, final, settings.get("pause_ms", 80), control.checkpoint)
                state["completed_chapters"][str(i)] = {"path": final.name, "sha256": file_hash(final)}
                save_json(manifest, state)
            report("Chapter completion", i, len(book.chapters))
        return manifest
    finally:
        backend.unload()
