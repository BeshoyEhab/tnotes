"""`tn completions install|uninstall` — shell completions + fish autoshow hook.

Completion scripts ship inside the package (completions_data/) so they are
available from any install: editable, pipx, uvx, or a wheel.
"""
import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path

_DATA = files("tnotes") / "completions_data"

def _home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home()))

def _xdg_config() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or _home() / ".config")

def _xdg_data() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or _home() / ".local" / "share")

def _shells_present() -> dict[str, bool]:
    which = shutil.which
    fish_dir = _xdg_config() / "fish"
    return {
        "fish": which("fish") is not None or fish_dir.is_dir(),
        "bash": which("bash") is not None,
        "zsh": which("zsh") is not None,
    }

def _targets(present: dict[str, bool]) -> list[tuple[str, Path, str]]:
    """(resource name, destination, label) for every shell we should set up."""
    out: list[tuple[str, Path, str]] = []
    if present.get("fish"):
        fish = _xdg_config() / "fish"
        out.append(("tn.fish", fish / "completions" / "tn.fish", "fish completion"))
        out.append(("tnotes-autoshow.fish", fish / "conf.d" / "tnotes-autoshow.fish",
                    "fish autoshow hook"))
    if present.get("bash"):
        out.append(("tn.bash", _xdg_data() / "bash-completion" / "completions" / "tn",
                    "bash completion"))
    if present.get("zsh"):
        out.append(("_tn", _home() / ".zsh" / "completions" / "_tn", "zsh completion"))
    return out

def _write(name: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        dest.unlink()  # never write through a symlink; replaces dangling ones
    dest.write_text((_DATA / name).read_text(encoding="utf-8"), encoding="utf-8")

def cmd_completions(args) -> int:
    action = getattr(args, "arg", None) or "install"
    if action not in ("install", "uninstall"):
        print("usage: tn completions [install|uninstall]", file=sys.stderr)
        return 1
    present = _shells_present()
    targets = _targets(present)
    if not targets:
        print("no supported shell detected (fish/bash/zsh) — nothing installed.")
        return 0
    for name, dest, label in targets:
        if action == "install":
            _write(name, dest)
            print(f"installed {label}: {dest}")
        else:
            try:
                dest.unlink()
            except FileNotFoundError:
                print(f"absent (skipped) {label}: {dest}")
                continue
            print(f"removed {label}: {dest}")
    if action == "install" and present.get("zsh"):
        print("zsh: add to ~/.zshrc if completions don't load:")
        print(f"  fpath=({_home() / '.zsh' / 'completions'} $fpath)")
        print("  autoload -Uz compinit && compinit")
    return 0
