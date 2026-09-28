import json
import os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("APPDATA", str(Path.home() / ".config"))) / "PDFBookReader" / "config.json"


def save_json(path: Path, value: dict):
    """Replace atomically so interruption cannot leave a partial manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
