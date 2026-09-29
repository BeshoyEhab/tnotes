"""tn CLI. Add paths in this task; list/show/search/picker in Tasks 5-6."""
import argparse
import os
import sys
import tempfile
from pathlib import Path
from . import store
from . import actions

def _split_tags(s: str | None) -> list[str]:
    return [t.strip() for t in s.split(",") if t.strip()] if s else []

def _read_stdin_if_piped() -> str | None:
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        return data if data.strip() else None
    return None

def compose_in_editor(entry_type: str, initial: str = "") -> str | None:
    header = (f"# tn {entry_type} — lines starting with # are ignored.\n"
              f"# Save+quit to save, quit with empty file to discard.\n")
    tmpl = {"url": "# URL: <paste url here>\n", "cmd": "# CMD: <paste command here>\n"}.get(entry_type, "")
    fd, tmp = tempfile.mkstemp(prefix="tn-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + tmpl + (initial or ""))
    if actions.edit_in_editor(tmp) != 0:
        print(f"editor exited non-zero; draft kept at {tmp}")
        return None
    lines = [ln for ln in Path(tmp).read_text(encoding="utf-8").splitlines()
             if not ln.lstrip().startswith("#")]
    text = "\n".join(lines).strip()
    try:
        Path(tmp).unlink()
    except OSError:
        pass
    return text or None

def _resolve_scope(args) -> tuple[str, str | None]:
    if args.g:
        return "global", None
    return "local", os.path.realpath(os.getcwd())

# NOTE (Task 4 fix): argparse cannot mix a top-level `text` positional with
# subparsers — `tn <text>` and `tn done <id>` both misparsed (invalid choice).
# So the quick-add positional is extracted here; build_parser has no `text`.
_SUB_COMMANDS = {"list", "search", "show", "open", "run", "edit", "rm",
                 "done", "undone", "hide", "unhide", "path"}
_VALUE_OPTIONS = {"--url", "--cmd", "--note", "--title", "--tags"}

def _extract_text(argv: list[str]) -> tuple[str | None, list[str]]:
    """Split raw argv into (quick-add text, remaining args for argparse)."""
    text = None
    rest: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in _VALUE_OPTIONS:
            rest.append(tok)
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                i += 1
                rest.append(argv[i])
        elif tok.startswith("-") and tok != "-":
            rest.append(tok)
        elif text is None:
            text = tok
        else:
            rest.append(tok)
        i += 1
    return text, rest

def cmd_add(args) -> int:
    etype = "note"
    if args.url is not None:
        etype = "url"
    elif args.cmd is not None:
        etype = "cmd"
    elif args.note is not None:
        etype = "note"
    body = args.url if etype == "url" else args.cmd if etype == "cmd" else args.note
    if body == "":
        body = None  # bare --url/--cmd/--note "": value still missing
    if body is None and args.text:
        body = args.text
    if body is None:
        body = _read_stdin_if_piped()
    if args.m:
        template_key = {"url": "URL: ", "cmd": "CMD: "}.get(etype, "")
        drafted = compose_in_editor(etype, (template_key + (body or "")) if body else "")
        if not drafted:
            print("discarded (empty).")
            return 1
        body = drafted
    if not body or not body.strip():
        print("error: empty entry; nothing saved.", file=sys.stderr)
        return 1
    body = body.strip()
    scope, cwd = _resolve_scope(args)
    title = args.title or (body.splitlines()[0][:60] if etype != "note" else body[:60])
    e = store.add_entry(type=etype, title=title, body=body,
                        tags=_split_tags(args.tags), scope=scope, cwd=cwd,
                        show_on_open=not args.no_show)
    print(f"saved {e['id']}")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tn", description="Terminal notepad with actions")
    p.add_argument("--url", nargs="?", const=None, default="__unset__", help="add URL entry")
    p.add_argument("--cmd", nargs="?", const=None, default="__unset__", help="add cmd entry")
    p.add_argument("--note", default=None, help="add note entry")
    p.add_argument("-g", action="store_true", help="global scope")
    p.add_argument("-l", action="store_true", help="local scope (this dir)")
    p.add_argument("--title", default=None)
    p.add_argument("--tags", default=None, help="comma-separated")
    p.add_argument("--no-show", action="store_true")
    p.add_argument("-m", action="store_true", help="compose in $EDITOR")
    p.add_argument("--all", action="store_true")
    p.add_argument("--done", action="store_true")
    p.add_argument("--hidden", action="store_true")
    p.add_argument("--startup", action="store_true")
    p.add_argument("--preview", action="store_true")
    sub = p.add_subparsers(dest="sub")
    for name in ["list", "search", "show", "open", "run", "edit", "rm",
                 "done", "undone", "hide", "unhide", "path"]:
        s = sub.add_parser(name)
        if name in ("search", "show", "open", "run", "edit", "rm",
                    "done", "undone", "hide", "unhide"):
            s.add_argument("arg", nargs="?")
        if name in ("open", "run"):
            s.add_argument("n", nargs="?", default="1")
        if name in ("list", "search", "show"):
            s.add_argument("--all", action="store_true")
            s.add_argument("-g", action="store_true")
            s.add_argument("-l", action="store_true")
            s.add_argument("--done", action="store_true")
            s.add_argument("--hidden", action="store_true")
            s.add_argument("--startup", action="store_true")
            s.add_argument("--preview", action="store_true")
    return p

def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else list(argv)
    if raw and raw[0] in _SUB_COMMANDS:
        args = build_parser().parse_args(raw)
        args.text = None
    else:
        text, rest = _extract_text(raw)
        args = build_parser().parse_args(rest)
        args.text = text
    if args.sub == "path":
        print(store.store_path())
        return 0
    if args.sub in ("done", "undone", "hide", "unhide"):
        try:
            mapping = {"done": {"status": "done"}, "undone": {"status": "active"},
                       "hide": {"show_on_open": False}, "unhide": {"show_on_open": True}}
            store.update_entry(args.arg, **mapping[args.sub])
            print(f"{args.sub} {args.arg}")
            return 0
        except KeyError:
            print(f"no entry {args.arg}", file=sys.stderr)
            return 1
    if args.sub == "rm":
        if store.delete_entry(args.arg):
            print(f"removed {args.arg}")
            return 0
        print(f"no entry {args.arg}", file=sys.stderr)
        return 1
    if args.sub == "edit":
        from .extract import extract_actions  # noqa: F401 (used Task 5)
        e = store.get_entry(args.arg)
        if not e:
            print(f"no entry {args.arg}", file=sys.stderr)
            return 1
        fd, tmp = tempfile.mkstemp(prefix="tn-edit-", suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"# editing {e['id']} — # lines ignored\n{e['body']}\n")
        if actions.edit_in_editor(tmp) != 0:
            print(f"editor exited non-zero; draft kept at {tmp}")
            return 1
        lines = [ln for ln in Path(tmp).read_text(encoding="utf-8").splitlines()
                 if not ln.lstrip().startswith("#")]
        new_body = "\n".join(lines).strip()
        try:
            Path(tmp).unlink()
        except OSError:
            pass
        if not new_body:
            print("discarded (empty).")
            return 1
        store.update_entry(e["id"], body=new_body,
                           title=new_body.splitlines()[0][:60])
        print(f"updated {e['id']}")
        return 0
    if args.sub is None and (args.url != "__unset__" or args.cmd != "__unset__"
                             or args.note is not None or args.text is not None or args.m
                             or not sys.stdin.isatty()):
        if args.url == "__unset__":
            args.url = None
        elif args.url is None:
            args.url = ""  # bare --url: typed, value missing (editor/stdin)
        if args.cmd == "__unset__":
            args.cmd = None
        elif args.cmd is None:
            args.cmd = ""  # bare --cmd: typed, value missing (editor/stdin)
        if args.url is None and args.cmd is None and args.note is None and args.text is None and not args.m:
            args.cmd = _read_stdin_if_piped()
            if args.cmd is None:
                print("usage: tn \"text\" | tn --url U | tn --cmd C | tn -m | tn list|search|show|open|run|...", file=sys.stderr)
                return 1
            return cmd_add(args)
        return cmd_add(args)
    # read paths + picker land in Tasks 5-6; stub keeps dispatch total
    from . import cli_read as _r  # lazy: created in Task 5
    return _r.dispatch(args)

if __name__ == "__main__":
    raise SystemExit(main())
