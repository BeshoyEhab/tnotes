"""fzf wrapper. Default here-only; --all for everywhere. Falls back to list."""
import os
import shutil
import subprocess
import sys
from .models import Entry
from .palette import ICONS


def has_fzf() -> bool:
    return shutil.which("fzf") is not None


def format_row(entry: Entry) -> str:
    icon = ICONS.get(entry.type, ICONS["note"])
    tags = " ".join(f"#{t}" for t in entry.tags)
    scope = "G" if entry.scope == "global" else "·"
    done = "✔ " if entry.status == "done" else ""
    tail = f"{scope}"
    if tags:
        tail = f"{tags} {tail}"
    return f"{done}{icon} {entry.title} {tail}".rstrip()

def build_rows(entries: list[Entry]) -> list[str]:
    return [f"{format_row(e)}\t{e.id}" for e in entries]

HEADER_KEYS = [("enter", "full"), ("o", "open"), ("r", "run"),
               ("c", "copy"), ("e", "edit"), ("ctrl-n", "new"), ("q", "quit")]
EXPECT_KEYS = [k for k, _ in HEADER_KEYS]

def header_bar() -> str:
    key_c, desc_c, reset = "\033[1;36m", "\033[2m", "\033[0m"
    return "  ".join(f"{key_c}{k}{reset} {desc_c}{v}{reset}" for k, v in HEADER_KEYS)

def fzf_argv() -> list[str]:
    tn = os.path.realpath(shutil.which("tn") or "tn")
    return ["fzf", "--delimiter=\t", "--with-nth=1", "--ansi",
            "--preview", f"{tn} show {{2}} --preview",
            "--preview-window=right:60%:wrap",
            "--header", header_bar(), "--header-border=rounded",
            "--print-query", f"--expect={','.join(EXPECT_KEYS)}"]


def pick_entry(entries: list[Entry], prompt: str = "select",
               header: str | None = None) -> Entry | None:
    """Pick one entry for a one-shot action (`tn done`, `tn rm`, ...).

    Uses fzf when available; otherwise asks for a number on a TTY. Returns
    None on cancel, empty input, or when there is no picker.
    """
    if not entries:
        return None
    if not has_fzf():
        if not sys.stdin.isatty():
            print("no picker available (fzf not found); use `tn <cmd> N`",
                  file=sys.stderr)
            return None
        for i, e in enumerate(entries, 1):
            print(f"{i}. {format_row(e)} {e.id}")
        try:
            n = int(input(f"{prompt} [1-{len(entries)}]: "))
        except (ValueError, EOFError, KeyboardInterrupt):
            return None
        return entries[n - 1] if 1 <= n <= len(entries) else None
    tn = os.path.realpath(shutil.which("tn") or "tn")
    argv = ["fzf", "--delimiter=\t", "--with-nth=1", "--ansi",
            "--preview", f"{tn} show {{2}} --preview",
            "--preview-window=right:60%:wrap",
            "--prompt", f"{prompt} > ",
            "--header", header or "enter select · esc cancel",
            "--header-border=rounded", "--no-multi"]
    proc = subprocess.run(argv, input="\n".join(build_rows(entries)).encode(),
                          capture_output=True)
    if proc.returncode not in (0, 1):
        return None
    lines = proc.stdout.decode().splitlines()
    if not lines:
        return None
    entry_id = lines[-1].split("\t")[-1].strip()
    return next((e for e in entries if e.id == entry_id), None)

def run_picker(entries: list[Entry]) -> tuple[str | None, str | None]:
    """Returns (key, entry_id). ctrl-n returns ("ctrl-n", query text)."""
    if not has_fzf():
        for e in entries:
            print(f"{format_row(e)} {e.id}")
        return None, None
    proc = subprocess.run(fzf_argv(), input="\n".join(build_rows(entries)).encode(),
                          capture_output=True)
    if proc.returncode not in (0, 1):
        return None, None  # 130 abort, 2 error
    lines = proc.stdout.decode().splitlines()
    if len(lines) < 2:
        return None, None  # query only or nothing: no key, no selection
    query, key = lines[0], lines[1].strip() or "enter"
    if len(lines) < 3:
        if key == "ctrl-n":
            return "ctrl-n", query
        return None, None  # accepted with no match: nothing to do
    entry_id = lines[2].split("\t")[-1].strip()
    if not entry_id:
        return None, None
    if key == "ctrl-n":
        return "ctrl-n", query
    return key, entry_id
