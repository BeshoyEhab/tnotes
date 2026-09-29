"""Read paths: list/search/show + preview rendering + pager."""
import os
import shutil
import subprocess
import sys
import textwrap
from . import store
from .extract import extract_actions
from .picker import format_row

def _autoshow_scope(args) -> tuple[str, bool]:
    if getattr(args, "g", False):
        return "global", False
    if getattr(args, "l", False):
        return "local", False
    return "here", False

def _entries_for(args, cwd=None):
    scope = "here"
    if getattr(args, "g", False):
        scope = "global"
    elif getattr(args, "l", False):
        scope = "local"
    return store.visible_entries(
        cwd=cwd, scope=scope,
        include_done=getattr(args, "done", False),
        include_hidden=True,
        all_dirs=getattr(args, "all", False))

def cmd_list(args) -> int:
    for e in _entries_for(args):
        print(f"{format_row(e)} {e['id']}")
    return 0

def cmd_search(args) -> int:
    q = (args.arg or "").lower()
    for e in _entries_for(args):
        if q in (e.get("title", "") + "\n" + e.get("body", "")).lower():
            print(f"{format_row(e)} {e['id']}")
    return 0

ICONS = {"url": "🔗", "cmd": "$", "note": "📝"}

def render_preview(entry: dict, actions: list[dict], max_lines: int = 100) -> str:
    icon = ICONS.get(entry.get("type"), "📝")
    tags = f" [{','.join(entry.get('tags', []))}]" if entry.get("tags") else ""
    scope = "(G)" if entry.get("scope") == "global" else "(·)"
    done = "✔ " if entry.get("status") == "done" else ""
    date = (entry.get("created") or "")[:10]
    lines = [f"{done}{icon} {entry.get('title', '')}{tags} {scope} {date}".rstrip()]
    if entry.get("type") in ("url", "cmd"):
        lines.append(entry.get("body", "").splitlines()[0] if entry.get("body") else "")
    show = "yes" if entry.get("show_on_open", True) else "no"
    lines.append(f"cwd: {entry.get('cwd') or '-'} / status: {entry.get('status')} / show: {show}")
    lines.append("---")
    lines.append("Actions:")
    oi = ri = 0
    for a in actions:
        if a["kind"] == "open":
            oi += 1
            lines.append(f" [o{oi}] open {a['target']}")
        else:
            ri += 1
            lines.append(f" [r{ri}] run {a['target']}")
    if not actions:
        lines.append(" (none — plain note)")
    lines.append(" [c] copy  [e] edit  [enter] full view")
    lines.append("---")
    lines.append("Body (wrapped):")
    body_lines = entry.get("body", "").splitlines() or [""]
    width = shutil.get_terminal_size((80, 24)).columns
    wrapped: list[str] = []
    for bl in body_lines:
        wrapped.extend(textwrap.wrap(bl, width) or [""])
    if len(wrapped) > max_lines:
        lines.extend(wrapped[:max_lines])
        lines.append(f"… (+{len(wrapped) - max_lines} lines, Enter for full)")
    else:
        lines.extend(wrapped)
    return "\n".join(lines) + "\n"

def render_full(entry: dict, actions: list[dict]) -> str:
    return render_preview(entry, actions, max_lines=10_000).replace(
        "… (+", "FULL — no truncation (+").replace(", Enter for full)", ")")

def _page(text: str) -> None:
    pager = os.environ.get("PAGER", "less -R")
    if not sys.stdout.isatty():
        print(text, end="")
        return
    if shutil.which("bat"):
        try:
            subprocess.run(["bat", "-p"], input=text.encode(), check=False)
            return
        except OSError:
            pass
    try:
        subprocess.run(pager.split(), input=text.encode(), check=False)
    except OSError:
        print(text, end="")

def cmd_show(args) -> int:
    if args.arg:  # show <id> [--preview]
        e = store.get_entry(args.arg)
        if not e:
            print(f"no entry {args.arg}", file=sys.stderr)
            return 1
        if getattr(args, "preview", False):
            sys.stdout.write(render_preview(e, extract_actions(e)))
        else:
            _page(render_full(e, extract_actions(e)))
        return 0
    entries = _entries_for(args)  # show (autoshow/manual)
    if getattr(args, "startup", False):
        entries = [e for e in entries
                   if e.get("status") == "active" and e.get("show_on_open", True)]
        if not entries:
            return 0  # silent when empty
    for e in entries:
        sys.stdout.write(render_preview(e, extract_actions(e)) + "\n")
    return 0

def dispatch(args) -> int:
    if args.sub == "list":
        return cmd_list(args)
    if args.sub == "search":
        return cmd_search(args)
    if args.sub == "show":
        return cmd_show(args)
    # open/run + bare picker land in Task 6
    from . import cli_actions as _a
    return _a.dispatch(args)
