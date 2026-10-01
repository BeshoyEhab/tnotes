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

def do_set_body(entry_id: str, body: str) -> Entry:
    e = resolve_entry(entry_id)
    return store.update_entry(e.id, body=body,
                              title=body.splitlines()[0][:60])

def do_remove(entry_id: str) -> bool:
    return store.delete_entry(resolve_entry(entry_id).id)

def compose_text(entry_type: str, initial: str = "") -> str | None:
    header = (f"# tn {entry_type} — lines starting with # are ignored.\n"
              f"# Save+quit to save, quit with empty file to discard.\n")
    tmpl = {"url": "# URL: <paste url here>\n", "cmd": "# CMD: <paste command here>\n"}.get(entry_type, "")
    fd, tmp = tempfile.mkstemp(prefix="tn-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + tmpl + (initial or ""))
    if actions.edit_in_editor(tmp) != 0:
        print(f"editor exited non-zero; draft kept at {tmp}")
        return None  # no unlink: draft preserved on purpose
    lines = [ln for ln in Path(tmp).read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    try:
        Path(tmp).unlink()
    except OSError:
        pass
    text = "\n".join(lines).strip()
    return text or None
