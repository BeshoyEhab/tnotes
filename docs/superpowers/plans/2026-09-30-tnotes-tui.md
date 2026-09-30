# tnotes textual TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the tn core (typed Entry, locked store, acyclic commands) and replace the one-shot fzf picker with a persistent textual TUI.

**Architecture:** `models` ← `config`/`store` ← `extract`/`actions` ← `commands` ← thin `cli*` + new `tui.py`; textual App with message-driven panes, `selection_actions` as the single capability source, workers/modals/suspend bridge for side effects.

**Tech Stack:** Python ≥3.12, `textual>=0.86` (TUI), `fzf` binary (fallback), `pytest` + `pytest-asyncio` (auto mode) for unit + Pilot tests, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-30-tnotes-tui-design.md` (amends `docs/superpowers/specs/2026-09-29-tnotes-design.md` UI path + stdlib-only rule only)

## Global Constraints

- Python ≥3.12. Core stays stdlib-only; `textual` is allowed for the TUI only, `fzf` binary remains as TUI fallback.
- JSONL store format and location unchanged (`~/.local/share/tnotes/tnotes.jsonl`, `TNOTES_DIR` override); one JSON per line; atomic temp+rename writes; new writes add `"schema_version": 2`.
- `Entry` fields (exact): `id type title body tags scope cwd status show_on_open created updated`; `id` 6-char lowercase hex; `scope ∈ {global,local}`; `status ∈ {active,done}`; `cwd` resolved absolute path for local, null for global.
- Non-interactive CLI behavior byte-identical (all existing pytest tests keep passing, updated only for Entry attribute access where they touch entries).
- Bare `tn` launches the TUI only when stdin AND stdout are ttys; pipes/non-tty/missing-textual keep fzf → list fallback.
- TDD every task; `pytest` green before each commit; frequent commits; never touch `~/.local/bin/note` or old fish files.

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | add `textual>=0.86`, dev group `pytest`+`pytest-asyncio`, `asyncio_mode="auto"` |
| `src/tnotes/models.py` | `Entry` dataclass, validation, `migrate`, `SCHEMA_VERSION=2`, `EntryNotFound`/`AmbiguousPrefix`/`NoActionError` |
| `src/tnotes/config.py` | live env readers: `data_dir() editor() browser() pager() autoshow_global()` |
| `src/tnotes/store.py` | Entry boundary, `fcntl` lock, keep atomic/match/corrupt behaviors |
| `src/tnotes/extract.py` | `extract_actions(entry: Entry)` (same rules) |
| `src/tnotes/commands.py` | pure command fns used by CLI and TUI; `compose_text` editor flow |
| `src/tnotes/cli*.py` | thin parsers/dispatchers delegating to `commands` |
| `src/tnotes/picker.py` | unchanged fallback (plus `format_row(entry: Entry)`) |
| `src/tnotes/tui.py` + `src/tnotes/tnotes.css` | textual app, widgets, messages, bridge |
| `tests/test_models.py test_config.py test_tui.py` | new; existing suites updated for Entry access |
| `README.md` | textual requirement, fallback chain, TUI keys |

Interface contracts (exact, cross-task):

```python
# models.py
@dataclass
class Entry:
    id: str; type: str = "note"; title: str = ""; body: str = ""
    tags: list[str] = field(default_factory=list)
    scope: str = "local"; cwd: str | None = None
    status: str = "active"; show_on_open: bool = True
    created: str = ""; updated: str = ""
    @classmethod
    def from_dict(cls, doc: dict) -> Entry: ...   # raises ValueError
    def to_dict(self) -> dict: ...                # includes schema_version: 2
    @staticmethod
    def migrate(doc: dict) -> dict: ...           # fills defaults for old lines
class EntryNotFound(Exception): ...
class AmbiguousPrefix(KeyError): ...
class NoActionError(Exception): ...
SCHEMA_VERSION = 2
```

```python
# config.py
def data_dir() -> Path
def editor() -> str          # $EDITOR -> $VISUAL -> "vi"
def browser() -> str | None  # $BROWSER or None
def pager() -> str           # $PAGER or "less -R"
def autoshow_global() -> bool  # NOTE_AUTOSHOW_GLOBAL == "1"
```

```python
# store.py (all Entry-typed)
def store_path() -> Path
def load_all() -> list[Entry]
def save_all(entries: list[Entry]) -> None
def add_entry(type, title, body, tags, scope, cwd, show_on_open) -> Entry
def get_entry(entry_id: str) -> Entry | None   # KeyError: ambiguous/empty
def update_entry(entry_id: str, **fields) -> Entry
def delete_entry(entry_id: str) -> bool        # KeyError: ambiguous propagates
def visible_entries(cwd=None, scope="here", include_done=False, include_hidden=False, all_dirs=False) -> list[Entry]
def generate_id(existing: set[str]) -> str
```

```python
# commands.py
def do_add(*, type, title, body, tags, scope, cwd, show_on_open) -> Entry
def do_list(*, scope="here", cwd=None, include_done=False, all_dirs=False) -> list[Entry]
def do_search(q, **filters) -> list[Entry]
def resolve_entry(entry_id: str) -> Entry      # raises EntryNotFound
def do_open(entry_id: str, n: int = 1) -> tuple[Entry, str]   # raises NoActionError
def do_run(entry_id: str, n: int = 1) -> tuple[Entry, str]    # raises NoActionError
def do_set_status(entry_id: str, status: str) -> Entry
def do_set_show(entry_id: str, show: bool) -> Entry
def do_remove(entry_id: str) -> bool
def compose_text(entry_type: str, initial: str = "") -> str | None
```

```python
# tui.py
def selection_actions(entry: Entry) -> dict  # {"opens": list[str], "runs": list[str]}
class TnotesApp(App): ...
```

---

### Task 1: Deps + models + config

**Files:**
- Modify: `pyproject.toml`
- Create: `src/tnotes/models.py`
- Create: `src/tnotes/config.py`
- Test: `tests/test_models.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (foundation).
- Produces: `models.Entry` + exceptions + `migrate`; all 5 `config` readers; textual importable. Tasks 2–5 build on these names verbatim.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
import pytest
from tnotes.models import Entry, SCHEMA_VERSION

def test_entry_round_trip():
    e = Entry(id="a1b2c3", type="url", title="t", body="https://x.example",
              tags=["a"], scope="global", cwd=None)
    d = Entry.from_dict(e.to_dict())
    assert d == e and e.to_dict()["schema_version"] == SCHEMA_VERSION == 2

def test_entry_rejects_bad_scope_status_id():
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "a1b2c3", "scope": "everywhere"})
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "a1b2c3", "status": "archived"})
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "XYZ"})

def test_migrate_fills_old_line():
    d = Entry.migrate({"id": "a1b2c3", "title": "t", "body": "b"})
    e = Entry.from_dict(d)
    assert (e.type, e.scope, e.status, e.show_on_open, e.tags) == ("note", "local", "active", True, [])
```

```python
# tests/test_config.py
from tnotes import config

def test_config_defaults(monkeypatch):
    for k in ("TNOTES_DIR", "EDITOR", "VISUAL", "BROWSER", "PAGER", "NOTE_AUTOSHOW_GLOBAL"):
        monkeypatch.delenv(k, raising=False)
    assert config.data_dir().name == "tnotes"
    assert config.editor() == "vi" and config.browser() is None
    assert config.pager() == "less -R" and config.autoshow_global() is False

def test_config_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setenv("EDITOR", "hx")
    monkeypatch.setenv("NOTE_AUTOSHOW_GLOBAL", "1")
    assert config.data_dir() == tmp_path and config.editor() == "hx"
    assert config.autoshow_global() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tnotes.models'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/tnotes/models.py
"""Typed Entry model. Sole schema definition; JSONL lines stay compatible."""
import re
from dataclasses import dataclass, field

SCHEMA_VERSION = 2
_ID_RE = re.compile(r"[0-9a-f]{6}")

class EntryNotFound(Exception):
    pass

class AmbiguousPrefix(KeyError):
    pass

class NoActionError(Exception):
    pass

@dataclass
class Entry:
    id: str
    type: str = "note"
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    scope: str = "local"
    cwd: str | None = None
    status: str = "active"
    show_on_open: bool = True
    created: str = ""
    updated: str = ""

    @staticmethod
    def migrate(doc: dict) -> dict:
        d = dict(doc)
        d.setdefault("type", "note")
        d.setdefault("title", "")
        d.setdefault("body", "")
        d.setdefault("tags", [])
        d.setdefault("scope", "local")
        d.setdefault("cwd", None)
        d.setdefault("status", "active")
        d.setdefault("show_on_open", True)
        d.setdefault("created", "")
        d.setdefault("updated", "")
        d["schema_version"] = d.get("schema_version", 1)
        return d

    @classmethod
    def from_dict(cls, doc: dict) -> Entry:
        d = cls.migrate(doc)
        if not isinstance(d["id"], str) or not _ID_RE.fullmatch(d["id"]):
            raise ValueError(f"bad id {d['id']!r}")
        if d["scope"] not in ("global", "local"):
            raise ValueError(f"bad scope {d['scope']!r}")
        if d["status"] not in ("active", "done"):
            raise ValueError(f"bad status {d['status']!r}")
        if not isinstance(d["type"], str) or not d["type"]:
            raise ValueError(f"bad type {d['type']!r}")
        return cls(id=d["id"], type=d["type"], title=d["title"], body=d["body"],
                   tags=list(d["tags"]), scope=d["scope"], cwd=d["cwd"],
                   status=d["status"], show_on_open=bool(d["show_on_open"]),
                   created=d["created"], updated=d["updated"])

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "title": self.title,
                "body": self.body, "tags": list(self.tags), "scope": self.scope,
                "cwd": self.cwd, "status": self.status,
                "show_on_open": self.show_on_open, "created": self.created,
                "updated": self.updated, "schema_version": SCHEMA_VERSION}
```

```python
# src/tnotes/config.py
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
```

`pyproject.toml` deltas (edit existing file): `dependencies = ["textual>=0.86"]`;
add `[dependency-groups] dev = ["pytest>=8", "pytest-asyncio>=0.23"]`; add
`asyncio_mode = "auto"` under `[tool.pytest.ini_options]`. Then run
`uv lock && uv sync` (network required — textual is fetched here).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py tests/test_config.py -q`
Expected: PASS (5 tests). Then `python -m pytest -q` — full suite still green (old tests untouched).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/tnotes/models.py src/tnotes/config.py tests/test_models.py tests/test_config.py
git commit -m "feat: add Entry model, central config, textual dependency"
```

---

### Task 2: Entry-typed store + locked writes + consumer migration

**Files:**
- Modify: `src/tnotes/store.py` (rewrite to Entry boundary + `fcntl` lock)
- Modify: `src/tnotes/extract.py` (`extract_actions(entry: Entry)`)
- Modify: `src/tnotes/picker.py` (`format_row(entry: Entry)` only)
- Modify: `src/tnotes/cli.py`, `src/tnotes/cli_read.py`, `src/tnotes/cli_actions.py` (mechanical `e["k"]` → `e.k`)
- Test: `tests/test_store.py` (update to Entry), `tests/test_extract.py`, `tests/test_cli.py`, `tests/test_picker.py`, `tests/test_actions.py` (mechanical updates)

**Interfaces:**
- Consumes: `models.Entry/from_dict/to_dict/migrate`, `AmbiguousPrefix`; `config.data_dir`.
- Produces: Entry-typed `store` API (contract above) that Tasks 3–5 call. No behavior change: same atomicity, same prefix rules, same filters, plus lock + corrupt-skip (already present).

- [ ] **Step 1: Update store tests to Entry access (they fail against dict store)**

```python
# tests/test_store.py — replace entry-dict assertions with attribute access, e.g.:
def test_add_entry_defaults_local_active_shown(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="buy milk", body="buy milk",
                        tags=[], scope="local", cwd="/tmp/x", show_on_open=True)
    assert isinstance(e, Entry)
    assert e.scope == "local" and e.cwd == "/tmp/x"
    assert e.status == "active" and e.show_on_open is True
```

Apply the same mechanical change to every test touching entries:
`e["id"]` → `e.id`, `e["title"]` → `e.title`, `e.get("tags", [])` → `e.tags`,
`store.update_entry(e["id"], ...)` → `store.update_entry(e.id, ...)`.
Also update `tests/test_extract.py` (build `Entry(...)` instead of dicts),
`tests/test_cli.py` (`store.get_entry(eid).type` etc.), `tests/test_picker.py`
(`format_row(Entry(...))`, `store.add_entry(...).id`).

- [ ] **Step 2: Run suite to verify failures**

Run: `python -m pytest -q`
Expected: FAILs wherever dict access meets new expectations (store still returns dicts).

- [ ] **Step 3: Rewrite store.py (Entry boundary + lock)**

```python
# src/tnotes/store.py
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

def _match(entries: list[Entry], entry_id: str) -> Entry | None:
    if not entry_id:
        raise KeyError(f"no entry {entry_id!r}")
    exact = [e for e in entries if e.id == entry_id]
    if exact:
        return exact[0]
    pref = [e for e in entries if e.id.startswith(entry_id)]
    if len(pref) == 1:
        return pref[0]
    if not pref:
        return None
    raise AmbiguousPrefix(f"ambiguous prefix {entry_id!r} ({len(pref)} matches)")

def get_entry(entry_id: str) -> Entry | None:
    with _locked():
        return _match(load_all(), entry_id)

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
    return out
```

`extract.py`: change signature to `def extract_actions(entry: Entry) -> list[dict]`
and replace `entry.get("type", "note")` → `entry.type`, `entry.get("body", "")` →
`entry.body`, `entry.get("title", "")` → `entry.title`.
`picker.format_row`: `entry.get(...)` → attributes (`entry.type`, `entry.tags`,
`entry.scope`, `entry.status`, `entry.title`).
`cli.py`/`cli_read.py`/`cli_actions.py`: mechanical `e["k"]` → `e.k`
(`e["id"]` → `e.id`, `e["body"]` → `e.body`, `e["title"]` → `e.title`,
`e.get("scope")` → `e.scope`, `e.get("cwd")` → `e.cwd`,
`e.get("status")` → `e.status`, `e.get("tags", [])` → `e.tags`,
`e.get("show_on_open", True)` → `e.show_on_open`,
`e.get("created")` → `e.created`, `e.get("type")` → `e.type`).
`actions.py`: unchanged (takes plain strings already).

- [ ] **Step 4: Run suite to verify green**

Run: `python -m pytest -q`
Expected: PASS (32 existing + new Task-1 tests = 37). Behavior identical; `tn list` smoke still works.

- [ ] **Step 5: Commit**

```bash
git add src/tnotes/store.py src/tnotes/extract.py src/tnotes/picker.py src/tnotes/cli.py src/tnotes/cli_read.py src/tnotes/cli_actions.py tests/
git commit -m "refactor: Entry-typed store with file locking, same behavior"
```

---

### Task 3: commands.py + thin CLI dispatchers

**Files:**
- Create: `src/tnotes/commands.py`
- Modify: `src/tnotes/cli.py`, `src/tnotes/cli_read.py`, `src/tnotes/cli_actions.py` (delegate to commands; keep all help text/flags)
- Test: `tests/test_commands.py` (new); existing CLI tests keep passing unmodified

**Interfaces:**
- Consumes: Entry-typed `store`, `extract`, `actions`, `compose` flow.
- Produces: `commands` contract above; `cli.compose_in_editor` stays importable (delegates to `commands.compose_text`). Task 4/5 call `commands` from the TUI.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_commands.py
import pytest
from tnotes import commands, store
from tnotes.models import EntryNotFound, NoActionError

def test_do_add_and_resolve(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="t", body="b", tags=["x"],
                        scope="global", cwd=None, show_on_open=True)
    assert isinstance(e, store.Entry) or hasattr(e, "id")
    assert commands.resolve_entry(e.id).id == e.id
    with pytest.raises(EntryNotFound):
        commands.resolve_entry("ffffff")

def test_do_open_picks_nth(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="n",
                        body="see https://a.example and https://b.example",
                        tags=[], scope="global", cwd=None, show_on_open=True)
    entry, url = commands.do_open(e.id, 2)
    assert url == "https://b.example"
    with pytest.raises(NoActionError):
        commands.do_run(e.id, 1)  # no run actions here

def test_do_remove_status_show(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="t", body="b", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert commands.do_set_status(e.id, "done").status == "done"
    assert commands.do_set_show(e.id, False).show_on_open is False
    assert commands.do_remove(e.id) is True
    with pytest.raises(EntryNotFound):
        commands.resolve_entry(e.id)
```

(`store.Entry` re-export: add `from .models import Entry` in store.py so the
`store.Entry` reference works; or use `models.Entry` — pick one and use it
in both test and code. Locked: `store.py` re-exports `Entry`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_commands.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tnotes.commands'`.

- [ ] **Step 3: Write commands.py + thin the CLI modules**

```python
# src/tnotes/commands.py
"""Pure command functions shared by the classic CLI and the TUI."""
import os
import tempfile
from pathlib import Path
from . import actions, store
from .extract import extract_actions
from .models import Entry, EntryNotFound, NoActionError

def do_add(*, type: str, title: str, body: str, tags: list[str],
           scope: str, cwd: str | None, show_on_open: bool) -> Entry:
    return store.add_entry(type=type, title=title, body=body, tags=list(tags),
                           scope=scope, cwd=cwd, show_on_open=show_on_open)

def do_list(*, scope: str = "here", cwd: str | None = None,
            include_done: bool = False, all_dirs: bool = False) -> list[Entry]:
    return store.visible_entries(cwd=cwd, scope=scope, include_done=include_done,
                                 include_hidden=True, all_dirs=all_dirs)

def do_search(q: str, **filters) -> list[Entry]:
    q = (q or "").lower()
    return [e for e in do_list(**filters)
            if q in (e.title + "\n" + e.body).lower()]

def resolve_entry(entry_id: str) -> Entry:
    try:
        e = store.get_entry(entry_id)
    except KeyError as exc:
        raise EntryNotFound(str(exc)) from exc
    if e is None:
        raise EntryNotFound(f"no entry {entry_id}")
    return e

def _nth(entry: Entry, kind: str, n: int) -> str:
    if n < 1:
        raise NoActionError(f"invalid index {n}")
    items = [a for a in extract_actions(entry) if a["kind"] == kind]
    if not 1 <= n <= len(items):
        raise NoActionError(f"no {kind} action #{n} on {entry.id}")
    return items[n - 1]["target"]

def do_open(entry_id: str, n: int = 1) -> tuple[Entry, str]:
    return (e := resolve_entry(entry_id)), _nth(e, "open", n)

def do_run(entry_id: str, n: int = 1) -> tuple[Entry, str]:
    return (e := resolve_entry(entry_id)), _nth(e, "run", n)

def do_set_status(entry_id: str, status: str) -> Entry:
    return store.update_entry(resolve_entry(entry_id).id, status=status)

def do_set_show(entry_id: str, show: bool) -> Entry:
    return store.update_entry(resolve_entry(entry_id).id, show_on_open=show)

def do_remove(entry_id: str) -> bool:
    return store.delete_entry(resolve_entry(entry_id).id)

def compose_text(entry_type: str, initial: str = "") -> str | None:
    header = (f"# tn {entry_type} — lines starting with # are ignored.\n"
              f"# Save+quit to save, quit with empty file to discard.\n")
    tmpl = {"url": "# URL: <paste url here>\n", "cmd": "# CMD: <paste command here>\n"}.get(entry_type, "")
    fd, tmp = tempfile.mkstemp(prefix="tn-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(header + tmpl + (initial or ""))
        if actions.edit_in_editor(tmp) != 0:
            print(f"editor exited non-zero; draft kept at {tmp}")
            return None
        lines = [ln for ln in Path(tmp).read_text(encoding="utf-8").splitlines()
                 if not ln.lstrip().startswith("#")]
        text = "\n".join(lines).strip()
        return text or None
    finally:
        if os.path.exists(tmp) and _compose_ok(tmp):
            try:
                Path(tmp).unlink()
            except OSError:
                pass
```

Wait — the draft-keep rule (Task 4 fix: unlink only on success path). The
`finally` + helper above is convoluted. Write it plainly instead:

```python
def compose_text(entry_type: str, initial: str = "") -> str | None:
    header = (f"# tn {entry_type} — lines starting with # are ignored.\n"
              f"# Save+quit to save, quit with empty file to discard.\n")
    tmpl = {"url": "# URL: <paste url here>\n", "cmd": "# CMD: <paste command here>\n"}.get(entry_type, "")
    fd, tmp = tempfile.mkstemp(prefix="tn-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + tmpl + (initial or ""))
    if actions.edit_in_editor(tmp) != 0:
        print(f"editor exited non-zero; draft kept at {tmp}")
        return None  # no unlink: draft preserved (see Task 4 fix)
    lines = [ln for ln in Path(tmp).read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    try:
        Path(tmp).unlink()
    except OSError:
        pass
    text = "\n".join(lines).strip()
    return text or None
```

Use the second (plain) version. `cli.compose_in_editor` becomes
`def compose_in_editor(entry_type: str, initial: str = "") -> str | None:
from .commands import compose_text; return compose_text(entry_type, initial)`
(top-level import fine — commands never imports cli).

Thin-out rule for `cli.py`/`cli_read.py`/`cli_actions.py` (apply per function,
behavior identical): replace `store.add_entry(...)` with
`commands.do_add(...)`; `store.visible_entries(...)` with `commands.do_list(...)`;
search filtering with `commands.do_search(...)`; `store.get_entry` + None-check
with `commands.resolve_entry` (catch `EntryNotFound` exactly where the old code
caught falsy/`KeyError`); `_nth(...)` blocks with `commands.do_open/do_run`
(catch `NoActionError` where old code printed `no ... action #`); state updates
with `do_set_status/do_set_show/do_remove`; editor temp-file flow with
`commands.compose_text`. Keep every flag, message string, and exit code.

- [ ] **Step 4: Run full suite to verify green**

Run: `python -m pytest -q`
Expected: PASS (all 37 + 3 new = 40). Spot-check CLI parity:
`TNOTES_DIR=$(mktemp -d) tn "x" && tn list && tn show --startup -l`.

- [ ] **Step 5: Commit**

```bash
git add src/tnotes/commands.py src/tnotes/cli.py src/tnotes/cli_read.py src/tnotes/cli_actions.py tests/test_commands.py
git commit -m "refactor: shared commands module, thin CLI dispatchers"
```

---

### Task 4: TUI shell (layout, browse, preview, responsive, entry rule)

**Files:**
- Create: `src/tnotes/tui.py`
- Create: `src/tnotes/tnotes.css`
- Modify: `src/tnotes/cli_actions.py` (TUI entry rule in `dispatch`)
- Test: `tests/test_tui.py` (Pilot browse tests)

**Interfaces:**
- Consumes: `commands.do_list`, `format_row`, `render_preview`-equivalent markdown source, scope flags from CLI args.
- Produces: `TnotesApp(scope, all_dirs, include_done)` with `current_entry`, `preview_source`, `keybar_plain` test seams; `refresh_entries(keep_selection=True)`. Task 5 adds actions + dynamic keybar.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tui.py
from textual.widgets import Markdown
from tnotes import store
from tnotes.tui import TnotesApp

def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="first", body="first-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    store.add_entry(type="note", title="second", body="second-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)

async def test_navigate_updates_preview(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_entry.title == "first"
        await pilot.press("j")
        await pilot.pause()
        assert app.current_entry.title == "second"
        assert "second-body" in app.preview_source

async def test_filter_narrows_list(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.click("#filter")  # focus; typing goes to Input
        await pilot.press(*"second")
        await pilot.pause()
        assert [e.title for e in app.visible] == ["second"]

async def test_compact_class_on_narrow(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test(size=(60, 24)) as pilot:
        await pilot.pause()
        assert app.has_class("compact")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tui.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tnotes.tui'`.

- [ ] **Step 3: Write minimal implementation (browse-only; actions land in Task 5)**

```python
# src/tnotes/tui.py
"""Persistent textual TUI. Browse shell in this task; actions in the next."""
import os
import sys
from dataclasses import dataclass
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, ListItem, ListView, Markdown, Static
from . import commands
from .models import Entry
from .picker import format_row

class EntrySelected(Message):
    def __init__(self, entry: Entry | None) -> None:
        super().__init__()
        self.entry = entry

@dataclass
class TnotesApp(App):
    ...
```

No — App subclasses take `__init__` params, not dataclass. Write it properly:

```python
class TnotesApp(App):
    CSS_PATH = "tnotes.css"
    BINDINGS = [("q", "quit", "quit"), ("/", "focus_filter", "filter"),
                ("j", "move_down", "down"), ("k", "move_up", "up")]

    def __init__(self, scope: str = "here", all_dirs: bool = False,
                 include_done: bool = False) -> None:
        super().__init__()
        self.scope = scope
        self.all_dirs = all_dirs
        self.include_done = include_done
        self.entries: list[Entry] = []
        self.visible: list[Entry] = []
        self.query: str = ""
        self.current_entry: Entry | None = None
        self.preview_source: str = ""
        self.keybar_plain: str = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="filter…", id="filter")
        with Horizontal(id="body"):
            yield ListView(id="entries")
            yield Markdown(id="preview")
        yield Static(id="keybar")

    async def on_mount(self) -> None:
        self.refresh_entries()
        self.update_keybar()

    def refresh_entries(self, keep_selection: bool = True) -> None:
        keep = self.current_entry.id if (keep_selection and self.current_entry) else None
        self.entries = commands.do_list(scope=self.scope, include_done=self.include_done,
                                        all_dirs=self.all_dirs)
        self.apply_filter()
        if keep:
            same = [e for e in self.visible if e.id == keep]
            self.select_entry(same[0] if same else (self.visible[0] if self.visible else None))
        elif self.visible:
            self.select_entry(self.visible[0])

    def apply_filter(self) -> None:
        q = self.query.lower()
        self.visible = [e for e in self.entries
                        if not q or q in (e.title + "\n" + e.body).lower()]
        lv = self.query_one("#entries", ListView)
        lv.clear()
        for e in self.visible:
            lv.append(ListItem(Label(format_row(e)), id=f"row-{e.id}"))
        if self.current_entry and self.current_entry.id not in {e.id for e in self.visible}:
            self.select_entry(self.visible[0] if self.visible else None)

    def select_entry(self, entry: Entry | None) -> None:
        self.current_entry = entry
        self.post_message(EntrySelected(entry))

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self.visible):
            self.select_entry(self.visible[idx])

    async def on_entry_selected(self, message: EntrySelected) -> None:
        src = self.preview_markdown(message.entry)
        self.preview_source = src
        await self.query_one("#preview", Markdown).update(src)
        self.update_keybar()

    @staticmethod
    def preview_markdown(entry: Entry | None) -> str:
        if entry is None:
            return "_No notes here yet — press `n` to add one._"
        head = f"## {entry.title or '(untitled)'}"
        meta = (f"{entry.type} · {entry.scope} · {entry.status} · "
                f"{'shown' if entry.show_on_open else 'hidden'}")
        tags = f"🏷️ {', '.join(entry.tags)}" if entry.tags else ""
        return "\n\n".join(p for p in [head, meta, tags, entry.body] if p)

    def update_keybar(self) -> None:
        # Task 5 makes this dynamic via selection_actions; static superset now.
        plain = "j/k navigate · / filter · n new · q quit"
        self.keybar_plain = plain
        self.query_one("#keybar", Static).update(plain)

    def on_resize(self, event: events.Resize) -> None:
        self.toggle_class("compact", event.size.width < 90)

    async def on_input_changed(self, event: Input.Changed) -> None:
        self.query = event.value
        self.apply_filter()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_move_down(self) -> None:
        self.query_one("#entries", ListView).action_cursor_down()

    def action_move_up(self) -> None:
        self.query_one("#entries", ListView).action_cursor_up()
```

```css
/* src/tnotes/tnotes.css */
#body { height: 1fr; }
#entries { width: 1fr; }
#preview { width: 2fr; }
#keybar { height: 1; background: $surface; color: $text-muted; }
TnotesApp.compact #body { layout: vertical; }
TnotesApp.compact #entries { height: 1fr; }
TnotesApp.compact #preview { height: 2fr; }
```

Entry rule in `cli_actions.dispatch` (replace the picker tail):

```python
    entries = _entries_for(args, cwd=None)
    if not entries:
        return _compose_new_note("")
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            from .tui import TnotesApp
        except ImportError:
            pass
        else:
            from .cli_read import _entries_for as _ef  # already imported; scope flags:
            app = TnotesApp(
                scope="global" if getattr(args, "g", False) else
                      "local" if getattr(args, "l", False) else "here",
                all_dirs=getattr(args, "all", False),
                include_done=getattr(args, "done", False))
            app.run()
            return 0
    key, eid = P.run_picker(entries)
    return _handle_picked(key, eid)
```

(Drop the now-dead `if not getattr(args, "hidden", False): pass` block — already
removed in the picker-ux work; if still present, delete it here.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_tui.py -q && python -m pytest -q`
Expected: PASS. Note: existing `dispatch` tests run under captured (non-tty)
stdout, so they keep hitting the fzf path — no test changes needed.

- [ ] **Step 5: Commit**

```bash
git add src/tnotes/tui.py src/tnotes/tnotes.css src/tnotes/cli_actions.py tests/test_tui.py
git commit -m "feat: textual TUI browse shell with live preview"
```

---

### Task 5: TUI actions (gated keys, submenu, modals, edit, docs)

**Files:**
- Modify: `src/tnotes/tui.py`, `src/tnotes/tnotes.css`
- Modify: `README.md` (textual requirement, fallback chain, TUI keys)
- Test: `tests/test_tui.py` (append Pilot action tests), `tests/test_selection.py` (new unit tests)

**Interfaces:**
- Consumes: `selection_actions`, `commands.do_*`, `actions.open_target/copy_text/run_command`, `TnotesApp` seams from Task 4.
- Produces: complete TUI per spec §4–§6. Nothing downstream.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selection.py
from tnotes.models import Entry
from tnotes.tui import selection_actions

def _e(**kw):
    base = dict(id="a1b2c3", type="note", title="t", body="")
    base.update(kw)
    return Entry(**base)

def test_note_links_and_cmds():
    acts = selection_actions(_e(body="see https://a.example, run `make test`"))
    assert acts == {"opens": ["https://a.example"], "runs": ["make test"]}

def test_plain_note_no_actions():
    assert selection_actions(_e(body="just text!")) == {"opens": [], "runs": []}

def test_typed_entries():
    assert selection_actions(_e(type="url", body="https://x.example"))["opens"] == ["https://x.example"]
    assert selection_actions(_e(type="cmd", body="make test"))["runs"] == ["make test"]
```

```python
# tests/test_tui.py (append)
from tnotes import store

async def _two(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="links", body="a https://a.example b https://b.example",
                    tags=[], scope="global", cwd=None, show_on_open=True)
    store.add_entry(type="note", title="plain", body="nothing", tags=[],
                    scope="global", cwd=None, show_on_open=True)

async def test_o_on_plain_does_nothing(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.press("j")  # select "plain"
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert app.current_entry.title == "plain"  # still here, no exit/crash

async def test_submenu_runs_second_action(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    import tnotes.tui as T
    picked = {}
    async def fake_run_worker(self, *a, **k):
        picked.update(k.get("marker", {}))
    monkeypatch.setattr(T.TnotesApp, "_run_open", lambda self, url: picked.update(url=url))
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()  # "links" selected
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("j", "enter")  # second URL
        await pilot.pause()
        assert picked.get("url") == "https://b.example"

async def test_done_toggle_refreshes(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert app.current_entry.status == "done"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_selection.py tests/test_tui.py -q`
Expected: FAIL (`selection_actions` undefined; `o`/`d` unbound).

- [ ] **Step 3: Write minimal implementation**

```python
# src/tnotes/tui.py additions
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import TextArea
from rich.text import Text
from . import actions
from .extract import extract_actions

def selection_actions(entry: Entry | None) -> dict:
    if entry is None:
        return {"opens": [], "runs": []
    }
    acts = extract_actions(entry)
    return {"opens": [a["target"] for a in acts if a["kind"] == "open"],
            "runs": [a["target"] for a in acts if a["kind"] == "run"]}

class ActionMenuScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "close")]

    def __init__(self, title: str, items: list[str]) -> None:
        super().__init__()
        self._title = title
        self._items = items

    def compose(self) -> ComposeResult:
        yield Label(self._title)
        yield ListView(*[ListItem(Label(t)) for t in self._items], id="menu")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.list_view.index)
```

Confirm modal:

```python
class ConfirmScreen(ModalScreen):
    BINDINGS = [("y", "confirm", "yes"), ("n", "dismiss", "no"),
                ("escape", "dismiss", "no")]

    def __init__(self, cmd: str) -> None:
        super().__init__()
        self._cmd = cmd

    def compose(self) -> ComposeResult:
        yield Label(f"run? [y/N]\n{self._cmd}")

    def action_confirm(self) -> None:
        self.dismiss(True)
```

App additions (methods + BINDINGS extend):
`[("o","open_link","open"),("r","run_cmd","run"),("c","copy_body","copy"),
("d","toggle_done","done"),("h","toggle_hide","hide"),("n","new_note","new"),
("e","edit_here","edit"),("E","edit_external","editor")]`.
`update_keybar` becomes dynamic:

```python
    def update_keybar(self) -> None:
        acts = selection_actions(self.current_entry)
        parts = [("j/k", "navigate"), ("/", "filter")]
        if acts["opens"]:
            parts.append(("o", f"open×{len(acts['opens'])}"))
        if acts["runs"]:
            parts.append(("r", f"run×{len(acts['runs'])}"))
        parts += [("c", "copy"), ("e", "edit"), ("d", "done"),
                  ("h", "hide"), ("n", "new"), ("q", "quit")]
        self.keybar_plain = " · ".join(f"{k} {v}" for k, v in parts)
        text = Text()
        for i, (k, v) in enumerate(parts):
            if i:
                text.append(" · ", style="dim")
            text.append(k, style="bold cyan")
            text.append(f" {v}", style="dim")
        self.query_one("#keybar", Static).update(text)
```

Gating: override `check_action`:

```python
    def check_action(self, action: str, parameters) -> bool | None:
        if self.current_entry is None and action in (
                "open_link", "run_cmd", "copy_body", "edit_here",
                "toggle_done", "toggle_hide"):
            return False
        acts = selection_actions(self.current_entry)
        if action == "open_link" and not acts["opens"]:
            return False
        if action == "run_cmd" and not acts["runs"]:
            return False
        return True
```

Primary + submenu + workers:

```python
    def _primary(self) -> tuple[str, str] | None:
        acts = selection_actions(self.current_entry)
        if acts["opens"]:
            return ("open", acts["opens"][0])
        if acts["runs"]:
            return ("run", acts["runs"][0])
        return None

    def action_open_link(self) -> None:
        acts = selection_actions(self.current_entry)["opens"]
        if len(acts) == 1:
            self._run_open(acts[0])
        elif acts:
            self.push_screen(ActionMenuScreen("open…", acts), self._menu_opened)

    def _menu_opened(self, idx: int | None) -> None:
        if idx is None:
            return
        self._run_open(selection_actions(self.current_entry)["opens"][idx])

    def _run_open(self, url: str) -> None:
        self.run_worker(lambda: actions.open_target(url), thread=True,
                        description=f"open {url}")
        self.notify(f"opening {url}")

    def action_run_cmd(self) -> None:
        acts = selection_actions(self.current_entry)["runs"]
        if len(acts) == 1:
            self._confirm_run(acts[0])
        elif acts:
            self.push_screen(ActionMenuScreen("run…", acts), self._menu_run)

    def _menu_run(self, idx: int | None) -> None:
        if idx is None:
            return
        self._confirm_run(selection_actions(self.current_entry)["runs"][idx])

    def _confirm_run(self, cmd: str) -> None:
        self.push_screen(ConfirmScreen(cmd), lambda yes: yes and self._run_cmd(cmd))

    def _run_cmd(self, cmd: str) -> None:
        def go():
            rc = actions.run_command(cmd, confirm=False)
            self.call_from_thread(self.notify, f"exit: {rc}")
        self.run_worker(go, thread=True, description=f"run {cmd}")

    def action_copy_body(self) -> None:
        if self.current_entry:
            body = self.current_entry.body
            self.run_worker(lambda: actions.copy_text(body), thread=True)
            self.notify("copied")

    def action_toggle_done(self) -> None:
        if self.current_entry:
            e = self.current_entry
            commands.do_set_status(e.id, "done" if e.status == "active" else "active")
            self.refresh_entries()

    def action_toggle_hide(self) -> None:
        if self.current_entry:
            e = self.current_entry
            commands.do_set_show(e.id, not e.show_on_open)
            self.refresh_entries()
```

In-place edit + new-note dialog + external editor:

```python
    def action_edit_here(self) -> None:
        if not self.current_entry:
            return
        self._editing = self.current_entry
        preview = self.query_one("#preview")
        self._editor = TextArea(self.current_entry.body, id="editor")
        self.query_one("#body", Horizontal).mount(self._editor, after=preview)
        preview.display = False
        self._editor.focus()

    # BINDINGS on the app can't scope to the editor; handle keys via message:
    async def on_key(self, event: events.Key) -> None:
        if getattr(self, "_editor", None) is not None and self._editor.has_focus:
            if event.key == "ctrl+s":
                event.prevent_default()
                self._save_edit()
            elif event.key == "escape":
                event.prevent_default()
                self._cancel_edit()

    def _save_edit(self) -> None:
        body = self._editor.text.strip()
        if body:
            commands.do_set_body(self._editing.id, body)  # see commands delta below
        self._close_editor()

    def _cancel_edit(self) -> None:
        self._close_editor()

    def _close_editor(self) -> None:
        self.query_one("#preview").display = True
        self._editor.remove()
        self._editor = None
        self.refresh_entries()

    def action_new_note(self) -> None:
        self.push_screen(NewNoteScreen(), self._new_saved)

    def _new_saved(self, data: tuple[str, str] | None) -> None:
        if not data:
            return
        title, body = data
        if not body.strip():
            self.notify("discarded (empty)", severity="warning")
            return
        import os
        commands.do_add(type="note", title=title or body.splitlines()[0][:60],
                        body=body.strip(), tags=[], scope="local",
                        cwd=os.path.realpath(os.getcwd()), show_on_open=True)
        self.refresh_entries(keep_selection=False)

    def action_edit_external(self) -> None:
        if not self.current_entry:
            return
        entry = self.current_entry
        with self.suspend():
            text = commands.compose_text(entry.type, initial=entry.body)
        if text and text.strip() and text.strip() != entry.body:
            commands.do_set_body(entry.id, text.strip())
        self.refresh_entries()
```

`NewNoteScreen` (modal with two Inputs):

```python
class NewNoteScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "cancel"), ("ctrl+s", "save", "save")]

    def compose(self) -> ComposeResult:
        yield Label("new note (ctrl-s save, esc cancel)")
        yield Input(placeholder="title (optional)", id="nt-title")
        yield TextArea(id="nt-body")

    def action_save(self) -> None:
        title = self.query_one("#nt-title", Input).value
        body = self.query_one("#nt-body", TextArea).text
        self.dismiss((title, body))
```

`commands.py` delta (add in this task):

```python
def do_set_body(entry_id: str, body: str) -> Entry:
    e = resolve_entry(entry_id)
    return store.update_entry(e.id, body=body,
                              title=body.splitlines()[0][:60])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_selection.py tests/test_tui.py -q && python -m pytest -q`
Expected: PASS. Manual (user, post-merge): colors, mouse click/wheel, `E`
suspend-edit round-trip, submenu with 3+ actions.

- [ ] **Step 5: Commit (code + README)**

README deltas: requirements table gains `textual (TUI; falls back to fzf)`;
install stays `uv sync`; add `## TUI keys` section listing the §4 keymap +
mouse + compact behavior.

```bash
git add src/tnotes/tui.py src/tnotes/tnotes.css src/tnotes/commands.py tests/test_tui.py tests/test_selection.py README.md
git commit -m "feat: TUI actions, submenu, in-place edit, docs"
```

---

## Self-Review

**1. Spec coverage:** §1 goal (persistent app, mouse, responsive, in-place edit,
multi-pick) → Tasks 4+5. §2 modules (models/config/store-lock/commands/tui/css,
textual dep, entry rule, fallback) → Tasks 1–4. §3 structure (layout, messages,
reactives, refresh, selection_actions, bridge, compact) → Tasks 4+5. §4
interaction (full keymap incl. `E` external — spec §4 lists `e` in-place; `E`
is a documented additive ruling, recorded here) → Task 5. §5 errors/testing/
install → Tasks 1–5 (Pilot + unit + README). §6 success criteria → Task 5
manual checklist + suite.
**2. Placeholder scan:** no TBD/TODO/"implement later"/"appropriate"/"similar
to Task N" — every step has exact code, commands, commits. One deliberate
`asyncio_mode="auto"` + network-for-uv-sync stated explicitly, not hand-waved.
**3. Type consistency:** `Entry` fields identical Tasks 1–5; `selection_actions`
shape `{"opens","runs"}` identical in contract/Task 5 tests/impl;
`commands.do_*` signatures identical in contract/Tasks 3–5;
`TnotesApp(scope,all_dirs,include_done)` + seams (`current_entry`,
`preview_source`, `keybar_plain`, `visible`, `refresh_entries`,
`update_keybar`) identical Tasks 4–5; `store.Entry` re-export locked in Task 3.
Fixed inline during writing: compose `finally`-unlink convoluted draft →
plain early-return version (matches Task-4 fix semantics).
