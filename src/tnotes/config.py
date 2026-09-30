"""Central environment resolution. All readers check env live (test-friendly)."""
import os
from pathlib import Path

def data_dir() -> Path:
    override = os.environ.get("TNOTES_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "tnotes"

def editor() -> str:
    return os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"

def browser() -> str | None:
    return os.environ.get("BROWSER") or None

def pager() -> str:
    return os.environ.get("PAGER") or "less -R"

def autoshow_global() -> bool:
    return os.environ.get("NOTE_AUTOSHOW_GLOBAL") == "1"
