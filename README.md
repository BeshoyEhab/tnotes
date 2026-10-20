# tnotes — terminal notepad with actions

`tn` stores typed entries (url, cmd, note) in JSONL and previews safely first,
then open / run / copy / edit from the terminal.

## Requirements

Required:

| Need | Version / note |
|---|---|
| Python | ≥ 3.12 (`requires-python = ">=3.12"`, stdlib only except `textual` for the TUI) |
| `fzf` binary | picker UI; without it `tn` falls back to `tn list` |
| `textual` | persistent TUI (`tn tui`); falls back to `fzf` picker without it |
| `uv` **or** `pip` | install only (`pip install -e .` needs network for the `hatchling` build backend) |
| `~/.local/bin` on your `PATH` | for the `tn` shim |

Optional (every one has a fallback — `tn` works without them):

| Need | Used for | Fallback |
|---|---|---|
| `bat` | full-entry view | plain text via `$PAGER` |
| `$PAGER` (e.g. `less -R`) | full-entry view, big notes | prints to stdout |
| `wl-copy` → `xclip` → `xsel` | `c` copy key | prints content + path |
| `xdg-open` → `$BROWSER` | `o` open key | prints the URL |
| `$EDITOR` → `$VISUAL` → `vi` | `-m` compose, `e` edit | — |
| `fish` | autoshow hook + completions | everything else works in any shell |
| `bash` / `zsh` | completions | — |

Environment variables: `TNOTES_DIR` (store dir, default
`~/.local/share/tnotes`), `EDITOR`/`VISUAL`, `BROWSER`, `PAGER`,
`NOTE_AUTOSHOW_GLOBAL=1` (autoshow globals too, default is this-dir only).

## Install

One line — clones to `~/tnotes`, links `tn`, installs shell completions +
the fish autoshow hook (re-run anytime; it updates in place):

```bash
curl -fsSL https://raw.githubusercontent.com/BeshoyEhab/tnotes/master/install.sh | bash
```

Or with a package manager:

```bash
pipx install git+https://github.com/BeshoyEhab/tnotes.git   # permanent install
tn completions install                                      # completions + autoshow

uvx --from git+https://github.com/BeshoyEhab/tnotes.git tn list   # try it, ephemeral
```

Or manually:

```bash
git clone https://github.com/BeshoyEhab/tnotes.git ~/tnotes && cd ~/tnotes
uv sync                             # or: pip install -e .
ln -sf ~/tnotes/.venv/bin/tn ~/.local/bin/tn
tn completions install              # fish/bash/zsh completions + fish autoshow
```

`tn completions install` detects the shells you have and writes:

| Shell | Files |
|---|---|
| fish | `~/.config/fish/completions/tn.fish`, `~/.config/fish/conf.d/tnotes-autoshow.fish` |
| bash | `~/.local/share/bash-completion/completions/tn` |
| zsh | `~/.zsh/completions/_tn` (plus a printed `fpath` hint for `~/.zshrc`) |

`tn completions uninstall` removes them again. From a checkout,
`python -m pytest -q` is an optional sanity check.

## Shell startup (automatic)

The conf.d hook shows each directory at most once per shell — revisits
stay silent, new dirs still show, and the initial shell directory is
covered too. No manual `config.fish` line needed; if you still have the
old `tn show --startup -l` one-liner, remove it to avoid double-showing.

## Usage (abridged)

tn "buy milk" | tn -g "pay bills" | tn --url URL --title T --tags a,b | tn --cmd "make test"
tn                      # picker here-only  tn --all # everywhere
tn list [--all] [-g|-l] [--done] [--hidden]
tn search Q [--all]     tn show [--startup] [-g|-l] [--done]
tn show ID|N [--preview]  tn open ID|N [n]  tn run ID|N [n]
tn edit ID|N | tn rm ID|N | tn done ID|N | tn undone ID|N | tn hide ID|N | tn unhide ID|N | tn path
tn done | tn undone | tn rm | tn hide | tn unhide   # pick one visually
tn completions [install|uninstall]     # shell completions + fish autoshow hook

ID|N = entry id (or unique prefix) or the row number from `tn list`
(numbers follow the list you read: `tn done N` = `tn list`, `tn undone N` =
`tn list --done`). With no ID/N, those action commands open the fzf picker
(or a numbered prompt on a plain TTY). done/undone print the remaining tasks
afterwards.

Env: TNOTES_DIR, EDITOR/VISUAL, BROWSER, PAGER, NOTE_AUTOSHOW_GLOBAL=1.

## TUI keys

`tn tui` opens the persistent browser (mouse click/wheel work; narrow
windows stack panes via the compact layout). Entries are grouped by
directory — `enter`/click a folder to expand it, `backspace` (or the
`^ parent` button) to go up. Every keybar action is also a
clickable button; clicking a row selects it, clicking a dialog field focuses
it. New notes open with the body focused so `enter` inserts a newline; the
title field is optional. Line breaks are kept in the editor and in TUI/CLI
previews, so a note you type on three lines stays three lines. Mouse needs
terminal support — inside tmux set `set -g mouse on`.

| Key | Action |
|---|---|
| `j` / `k` | navigate entries |
| `enter` | open/run the selected entry, or expand a folder |
| `/` | focus filter |
| `o` | open first link, or pick from submenu when several |
| `r` | run first command (with confirm), or pick from submenu |
| `c` | copy body to clipboard |
| `e` | in-place edit (`ctrl-s` save, `esc` cancel) |
| `E` | external `$EDITOR` round-trip |
| `d` | toggle done/active |
| `h` | toggle hide/show-on-open |
| `n` | new note dialog (`ctrl-s` save, `esc` cancel) |
| `backspace` | browse parent directory |
| `q` | quit |
