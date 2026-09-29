"""JSONL persistence. Store: $TNOTES_DIR/tnotes.jsonl or ~/.local/share/tnotes/tnotes.jsonl."""
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

def data_dir() -> Path:
    override = os.environ.get("TNOTES_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "tnotes"

def store_path() -> Path:
    return data_dir() / "tnotes.jsonl"

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def generate_id(existing: set[str]) -> str:
    while True:
        cand = secrets.token_hex(3)  # 6 lowercase hex chars
        if cand not in existing:
            return cand

def load_all() -> list[dict]:
    p = store_path()
    if not p.exists():
        return []
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries

def save_all(entries: list[dict]) -> None:
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(d), prefix="tnotes-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, store_path())
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

def add_entry(type: str, title: str, body: str, tags: list[str],
              scope: str, cwd: str | None, show_on_open: bool) -> dict:
    entries = load_all()
    now = _now_iso()
    entry = {
        "id": generate_id({e["id"] for e in entries}),
        "type": type, "title": title, "body": body, "tags": list(tags),
        "scope": scope, "cwd": cwd, "status": "active",
        "show_on_open": show_on_open, "created": now, "updated": now,
    }
    entries.append(entry)
    save_all(entries)
    return entry

def get_entry(entry_id: str) -> dict | None:
    for e in load_all():
        if e["id"] == entry_id or e["id"].startswith(entry_id):
            return e
    return None

def update_entry(entry_id: str, **fields) -> dict:
    entries = load_all()
    for e in entries:
        if e["id"] == entry_id or e["id"].startswith(entry_id):
            e.update(fields)
            e["updated"] = _now_iso()
            save_all(entries)
            return e
    raise KeyError(f"no entry {entry_id}")

def delete_entry(entry_id: str) -> bool:
    entries = load_all()
    kept = [e for e in entries if not (e["id"] == entry_id or e["id"].startswith(entry_id))]
    if len(kept) == len(entries):
        return False
    save_all(kept)
    return True

def visible_entries(cwd: str | None = None, scope: str = "here",
                    include_done: bool = False, include_hidden: bool = False,
                    all_dirs: bool = False) -> list[dict]:
    if cwd is None:
        cwd = os.path.realpath(os.getcwd())
    out = []
    for e in load_all():
        if e.get("status") == "done" and not include_done:
            continue
        if not e.get("show_on_open", True) and not include_hidden:
            continue
        if all_dirs:
            out.append(e)
            continue
        if scope == "global":
            if e.get("scope") == "global":
                out.append(e)
        elif scope == "local":
            if e.get("scope") == "local" and e.get("cwd") == cwd:
                out.append(e)
        else:  # here
            if e.get("scope") == "global":
                out.append(e)
            elif e.get("scope") == "local" and e.get("cwd") == cwd:
                out.append(e)
    return out
