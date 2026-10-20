"""Read paths: list/search/show + preview rendering + pager."""
import os
import shutil
import subprocess
import sys
import textwrap
from . import commands
from .extract import extract_actions
from .models import Entry, EntryNotFound
from .palette import FAINT, FG, GREEN, ICONS, ORANGE, PURPLE, TYPE_COLORS
from .textfmt import preserve_linebreaks

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
    return commands.do_list(
        cwd=cwd, scope=scope,
        include_done=getattr(args, "done", False),
        all_dirs=getattr(args, "all", False))

def _color_enabled() -> bool:
    """ANSI color only for interactive terminals: never into pipes, dumb
    terminals, or when NO_COLOR is set (https://no-color.org)."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False

def _fg(hex_color: str, text: str, *, bold: bool = False,
        dim: bool = False, strike: bool = False) -> str:
    """Truecolor foreground; callers gate this behind _color_enabled()."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    codes = []
    if bold:
        codes.append("1")
    if dim:
        codes.append("2")
    if strike:
        codes.append("9")
    codes.append(f"38;2;{r};{g};{b}")
    return f"\033[{';'.join(codes)}m{text}\033[0m"

def _tags_out(entry: Entry, color: bool) -> str:
    if not entry.tags:
        return ""
    if not color:
        return " " + " ".join(f"#{t}" for t in entry.tags)
    return "".join(_fg(PURPLE, f" #{t}") for t in entry.tags)

def _row_out(entry: Entry, color: bool, number: int | None = None) -> str:
    icon = ICONS.get(entry.type, ICONS["note"])
    done = entry.status == "done"
    tags = _tags_out(entry, color)
    scope = " G" if entry.scope == "global" else ""
    if not color:
        prefix = f"{number}. " if number is not None else ""
        check = "✔ " if done else ""
        return f"{prefix}{check}{icon} {entry.title}{tags}{scope} · {entry.id}"
    parts = []
    if number is not None:
        parts.append(_fg(FAINT, f"{number}. "))
    if done:
        parts.append(_fg(GREEN, "✔ ", bold=True))
    parts.append(_fg(TYPE_COLORS.get(entry.type, GREEN), icon))
    parts.append(" ")
    parts.append(_fg(FG, entry.title, strike=done))
    if tags:
        parts.append(tags)
    if scope:
        parts.append(_fg(ORANGE, scope, bold=True))
    parts.append(_fg(FAINT, f" · {entry.id}"))
    return "".join(parts)

def cmd_list(args) -> int:
    color = _color_enabled()
    for i, e in enumerate(_entries_for(args), 1):
        print(_row_out(e, color, number=i))
    return 0

def print_active_list() -> None:
    """The numbered remaining-task list (`tn list`), reused after done/undone."""
    color = _color_enabled()
    for i, e in enumerate(commands.do_list(), 1):
        print(_row_out(e, color, number=i))

def cmd_search(args) -> int:
    scope = "here"
    if getattr(args, "g", False):
        scope = "global"
    elif getattr(args, "l", False):
        scope = "local"
    color = _color_enabled()
    for e in commands.do_search(
            args.arg or "", scope=scope, cwd=None,
            include_done=getattr(args, "done", False),
            all_dirs=getattr(args, "all", False)):
        print(_row_out(e, color))
    return 0

def render_preview(entry: Entry, actions: list[dict], max_lines: int = 100) -> str:
    icon = ICONS.get(entry.type, ICONS["note"])
    tags = " " + " ".join(f"#{t}" for t in entry.tags) if entry.tags else ""
    scope = "(G)" if entry.scope == "global" else ""
    done = "✔ " if entry.status == "done" else ""
    date = (entry.created or "")[:10]
    lines = [f"{done}{icon} {entry.title}{tags} {scope} {date}".rstrip()]
    if entry.type in ("url", "cmd"):
        lines.append(entry.body.splitlines()[0] if entry.body else "")
    show = "yes" if entry.show_on_open else "no"
    lines.append(f"cwd: {entry.cwd or '-'} / status: {entry.status} / show: {show}")
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
    body_lines = entry.body.splitlines() or [""]
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

def render_full(entry: Entry, actions: list[dict]) -> str:
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

def _rich_preview(text: str) -> str:
    """Render preview markdown with color via mdcat when suitable, else plain."""
    if not shutil.which("mdcat"):
        return text
    if not (sys.stdout.isatty() or "FZF_PREVIEW_COLUMNS" in os.environ):
        return text  # piped elsewhere: keep output clean
    cmd = ["mdcat", "--ansi", "-l"]
    cols = os.environ.get("FZF_PREVIEW_COLUMNS", "")
    if cols.isdigit():
        cmd += ["--columns", cols]
    # The preview is deliberately line-oriented; mdcat would otherwise collapse
    # every soft line break into one paragraph.
    text = preserve_linebreaks(text)
    try:
        p = subprocess.run(cmd, input=text.encode(), capture_output=True)
    except OSError:
        return text
    if p.returncode != 0 or not p.stdout:
        return text
    return p.stdout.decode()

def _startup_compact(entries: list[Entry], only_global: bool = False,
                     only_local: bool = False, color: bool = False) -> str:
    """Old-note style greeting: numbered one-liners under section headers.
    One continuous 1..N count across sections — matches `tn list` / `tn done N`."""
    head = (lambda s: _fg(ORANGE, s, bold=True)) if color else (lambda s: s)
    out: list[str] = []
    n = 0
    if not only_local:
        g = [e for e in entries if e.scope == "global"]
        if g:
            out.append(head("Global notes:"))
            for e in g:
                n += 1
                out.append("  " + _row_out(e, color, number=n))
    if not only_global:
        loc = [e for e in entries if e.scope != "global"]
        if loc:
            if out:
                out.append("")
            cwd = os.path.realpath(os.getcwd())
            out.append(head(f"This folder ({cwd}):"))
            for e in loc:
                n += 1
                out.append("  " + _row_out(e, color, number=n))
    return "\n".join(out) + "\n" if out else ""

def cmd_show(args) -> int:
    if args.arg:  # show <id> [--preview]
        try:
            # numbers follow the view you asked for: `tn list` or `tn list --done`
            e = commands.resolve_entry(
                args.arg,
                numeric_mode="all" if getattr(args, "done", False) else "active")
        except EntryNotFound as exc:
            print(exc, file=sys.stderr)
            return 1
        if getattr(args, "preview", False):
            sys.stdout.write(_rich_preview(render_preview(e, extract_actions(e))))
        else:
            _page(render_full(e, extract_actions(e)))
        return 0
    entries = _entries_for(args)  # show (autoshow/manual)
    if getattr(args, "startup", False):
        entries = [e for e in entries
                   if e.status == "active" and e.show_on_open]
        if not entries:
            return 0  # silent when empty
        sys.stdout.write(_startup_compact(
            entries, only_global=getattr(args, "g", False),
            only_local=getattr(args, "l", False),
            color=_color_enabled()))
        return 0
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
    # open/run + bare picker dispatch.
    from . import cli_actions as _a
    return _a.dispatch(args)
