"""JSONL persistence over Entry objects. Exclusive lock around read-modify-write."""
import fcntl
import json
import os
import secrets
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from . import config
from .models import AmbiguousPrefix, Entry

def store_path() -> Path:
    return config.data_dir() / "tnotes.jsonl"

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def generate_id(existing: set[str]) -> str:
    while True:
        cand = secrets.token_hex(3)
        if cand not in existing:
            return cand

@contextmanager
def _locked():
    d = config.data_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".lock", "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def load_all() -> list[Entry]:
    p = store_path()
    if not p.exists():
        return []
    entries = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append(Entry.from_dict(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"warning: skipping corrupt line {lineno} in {p}: {exc}", file=sys.stderr)
    return entries

def save_all(entries: list[Entry]) -> None:
    d = config.data_dir()
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(d), prefix="tnotes-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")
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
              scope: str, cwd: str | None, show_on_open: bool) -> Entry:
    with _locked():
        entries = load_all()
        now = _now_iso()
        entry = Entry(id=generate_id({e.id for e in entries}), type=type,
                      title=title, body=body, tags=list(tags), scope=scope,
                      cwd=cwd, status="active", show_on_open=show_on_open,
                      created=now, updated=now)
        entries.append(entry)
        save_all(entries)
        return entry

def _match(entries: list[Entry], entry_id: str, *, prefix: bool = True) -> Entry | None:
    if not entry_id:
        raise KeyError(f"no entry {entry_id!r}")
    exact = [e for e in entries if e.id == entry_id]
    if exact:
        return exact[0]
    if not prefix:
        return None
    pref = [e for e in entries if e.id.startswith(entry_id)]
    if len(pref) == 1:
        return pref[0]
    if not pref:
        return None
    raise AmbiguousPrefix(f"ambiguous prefix {entry_id!r} ({len(pref)} matches)")

def get_entry(entry_id: str, *, prefix: bool = True) -> Entry | None:
    with _locked():
        return _match(load_all(), entry_id, prefix=prefix)

def update_entry(entry_id: str, **fields) -> Entry:
    with _locked():
        entries = load_all()
        e = _match(entries, entry_id)
        if e is None:
            raise KeyError(f"no entry {entry_id}")
        for k, v in fields.items():
            if k in ("id", "created"):
                continue  # immutable; silently ignore (was: unguarded overwrite)
            setattr(e, k, v)
        e.updated = _now_iso()
        save_all(entries)
        return e

def delete_entry(entry_id: str) -> bool:
    with _locked():
        entries = load_all()
        e = _match(entries, entry_id)  # AmbiguousPrefix propagates
        if e is None:
            return False
        save_all([x for x in entries if x.id != e.id])
        return True

def visible_entries(cwd: str | None = None, scope: str = "here",
                    include_done: bool = False, include_hidden: bool = False,
                    all_dirs: bool = False) -> list[Entry]:
    if cwd is None:
        cwd = os.path.realpath(os.getcwd())
    out = []
    with _locked():
        entries = load_all()
    for e in entries:
        if e.status == "done" and not include_done:
            continue
        if not e.show_on_open and not include_hidden:
            continue
        if all_dirs:
            out.append(e)
            continue
        if scope == "global":
            if e.scope == "global":
                out.append(e)
        elif scope == "local":
            if e.scope == "local" and e.cwd == cwd:
                out.append(e)
        else:
            if e.scope == "global" or (e.scope == "local" and e.cwd == cwd):
                out.append(e)
    # canonical order: global first, then locals (stable) — list, startup,
    # picker and numeric addresses all count this same sequence
    out.sort(key=lambda e: e.scope != "global")
    return out
