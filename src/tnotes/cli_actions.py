"""Picker entry + open/run/copy/edit key handling."""
import os
import sys
from . import actions, commands
from .extract import extract_actions
from . import picker as P
from .models import EntryNotFound, NoActionError
from .cli_read import render_full, _page, _entries_for

def cmd_open(args) -> int:
    try:
        n = int(getattr(args, "n", 1) or 1)
    except (ValueError, TypeError):
        print(f"invalid index {getattr(args, 'n', None)!r}", file=sys.stderr)
        return 1
    try:
        e, target = commands.do_open(args.arg, n)
    except EntryNotFound as exc:
        print(exc, file=sys.stderr)
        return 1
    except NoActionError as exc:
        print(exc, file=sys.stderr)
        return 1
    return actions.open_target(target)

def cmd_run(args) -> int:
    try:
        n = int(getattr(args, "n", 1) or 1)
    except (ValueError, TypeError):
        print(f"invalid index {getattr(args, 'n', None)!r}", file=sys.stderr)
        return 1
    try:
        e, target = commands.do_run(args.arg, n)
    except EntryNotFound as exc:
        print(exc, file=sys.stderr)
        return 1
    except NoActionError as exc:
        print(exc, file=sys.stderr)
        return 1
    return actions.run_command(target, confirm=True)

def _compose_new_note(initial: str) -> int:
    from .cli import compose_in_editor
    text = compose_in_editor("note", initial=initial)
    if not text or not text.strip():
        print("discarded (empty).")
        return 1
    body = text.strip()
    e = commands.do_add(type="note", title=body.splitlines()[0][:60], body=body,
                        tags=[], scope="local",
                        cwd=os.path.realpath(os.getcwd()), show_on_open=True)
    print(f"saved {e.id}")
    return 0

def _handle_picked(key: str | None, entry_id: str | None) -> int:
    if key == "ctrl-n":
        return _compose_new_note(entry_id or "")
    if not entry_id:
        return 0 if key is None else 1
    try:
        e = commands.resolve_entry(entry_id)
    except EntryNotFound:
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
        actions.copy_text(e.body)
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
    if not entries:
        return _compose_new_note("")  # nothing to pick: straight to editor
    key, eid = P.run_picker(entries)
    return _handle_picked(key, eid)
