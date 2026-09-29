"""Picker entry + open/run/copy/edit key handling."""
import sys
from . import store, actions
from .extract import extract_actions
from . import picker as P
from .cli_read import render_full, _page, _entries_for

def _nth(actions_list: list[dict], kind: str, n: int) -> dict | None:
    items = [a for a in actions_list if a["kind"] == kind]
    return items[n - 1] if 1 <= n <= len(items) else None

def cmd_open(args) -> int:
    e = store.get_entry(args.arg)
    if not e:
        print(f"no entry {args.arg}", file=sys.stderr)
        return 1
    n = int(getattr(args, "n", 1) or 1)
    target = _nth(extract_actions(e), "open", n)
    if not target:
        print(f"no open action #{n} on {e['id']}", file=sys.stderr)
        return 1
    return actions.open_target(target["target"])

def cmd_run(args) -> int:
    e = store.get_entry(args.arg)
    if not e:
        print(f"no entry {args.arg}", file=sys.stderr)
        return 1
    n = int(getattr(args, "n", 1) or 1)
    target = _nth(extract_actions(e), "run", n)
    if not target:
        print(f"no run action #{n} on {e['id']}", file=sys.stderr)
        return 1
    return actions.run_command(target["target"], confirm=True)

def _handle_picked(key: str | None, entry_id: str | None) -> int:
    if not entry_id:
        return 0 if key is None else 1
    e = store.get_entry(entry_id)
    if not e:
        return 1
    acts = extract_actions(e)
    if key in (None, "", "enter"):
        _page(render_full(e, acts))
        return 0
    if key == "o":
        first = next((a for a in acts if a["kind"] == "open"), None)
        return actions.open_target(first["target"]) if first else 1
    if key == "r":
        first = next((a for a in acts if a["kind"] == "run"), None)
        return actions.run_command(first["target"], confirm=True) if first else 1
    if key == "c":
        actions.copy_text(e["body"])
        return 0
    if key == "e":
        from .cli import main as _main
        return _main(["edit", entry_id])
    return 0  # q/quit

def dispatch(args) -> int:
    if args.sub == "open":
        return cmd_open(args)
    if args.sub == "run":
        return cmd_run(args)
    # bare tn picker: tn [--all] [-g|-l] [--done] [--hidden]
    entries = _entries_for(args, cwd=None)
    if not getattr(args, "hidden", False):
        pass  # picker shows hidden by default (include_hidden=True in _entries_for)
    key, eid = P.run_picker(entries)
    return _handle_picked(key, eid)
