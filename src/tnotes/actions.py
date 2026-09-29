"""Side-effect backends. Order: opener xdg-open->$BROWSER;
clipboard wl-copy->xclip->xsel; editor $EDITOR->$VISUAL->vi."""
import os
import shutil
import subprocess

def find_exe(names: list[str]) -> str | None:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None

def open_target(url: str) -> int:
    opener = find_exe(["xdg-open"])
    if opener:
        return subprocess.run([opener, url]).returncode
    browser = os.environ.get("BROWSER")
    if browser:
        return subprocess.run(browser.split() + [url]).returncode
    print(f"no opener (xdg-open/$BROWSER) — URL:\n{url}")
    return 1

def run_command(cmd: str, confirm: bool = True) -> int:
    if confirm:
        ans = input(f"run? [y/N] {cmd}\n> ").strip().lower()
        if ans not in ("y", "yes"):
            print("aborted.")
            return 130
    p = subprocess.run(cmd, shell=True)
    print(f"exit: {p.returncode}")
    return p.returncode

def copy_text(text: str) -> bool:
    if find_exe(["wl-copy"]):
        subprocess.run(["wl-copy"], input=text.encode(), check=False)
        return True
    if find_exe(["xclip"]):
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=False)
        return True
    if find_exe(["xsel"]):
        subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=False)
        return True
    print("no clipboard tool (wl-copy/xclip/xsel) — content:\n" + text)
    return False

def edit_in_editor(path) -> int:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    return subprocess.run([editor, str(path)]).returncode
