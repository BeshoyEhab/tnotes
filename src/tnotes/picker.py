"""fzf wrapper. Default here-only; --all for everywhere. Falls back to list."""
import os
import shutil
import subprocess


def has_fzf() -> bool:
    return shutil.which("fzf") is not None


def format_row(entry: dict) -> str:
    icons = {"url": "🔗", "cmd": "$", "note": "📝"}
    icon = icons.get(entry.get("type"), "📝")
    tags = f" [{','.join(entry.get('tags', []))}]" if entry.get("tags") else ""
    scope = "G" if entry.get("scope") == "global" else "·"
    done = "✔ " if entry.get("status") == "done" else ""
    return f"{done}{icon} {entry.get('title', '')}{tags} {scope}".rstrip()

def build_rows(entries: list[dict]) -> list[str]:
    return [f"{format_row(e)}\t{e['id']}" for e in entries]

def run_picker(entries: list[dict]) -> tuple[str | None, str | None]:
    """Returns (key, entry_id). key in enter/o/r/c/e/q or None on abort/fallback."""
    if not entries:
        print("no notes here yet — tn \"text\" to add one.")
        return None, None
    if not has_fzf():
        for e in entries:
            print(f"{format_row(e)} {e['id']}")
        return None, None
    tn = os.path.realpath(shutil.which("tn") or "tn")
    proc = subprocess.run(
        ["fzf", "--delimiter=\t", "--with-nth=1",
         "--preview", f"{tn} show {{2}} --preview",
         "--preview-window=right:60%:wrap",
         "--expect=enter,o,r,c,e,q"],
        input="\n".join(build_rows(entries)).encode(),
        capture_output=True)
    lines = proc.stdout.decode().splitlines()
    if len(lines) < 2:
        return None, None
    key = lines[0].strip() or "enter"
    entry_id = lines[1].split("\t")[-1].strip()
    return key, entry_id
