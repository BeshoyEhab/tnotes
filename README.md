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
| `bash` / `zsh` | completions (`completions/tn.bash`, `completions/_tn`) | — |

Environment variables: `TNOTES_DIR` (store dir, default
`~/.local/share/tnotes`), `EDITOR`/`VISUAL`, `BROWSER`, `PAGER`,
`NOTE_AUTOSHOW_GLOBAL=1` (autoshow globals too, default is this-dir only).

## Install

```bash
git clone <repo-url> ~/tnotes && cd ~/tnotes
uv sync                             # or: pip install -e .
ln -sf ~/tnotes/.venv/bin/tn ~/.local/bin/tn   # or wherever your pipx/uv-tool tn lives
mkdir -p ~/.config/fish/conf.d ~/.config/fish/completions
ln -sf ~/tnotes/fish/conf.d/tnotes-autoshow.fish ~/.config/fish/conf.d/
ln -sf ~/tnotes/fish/completions/tn.fish ~/.config/fish/completions/
# bash:  source ~/tnotes/completions/tn.bash   # from ~/.bashrc
# zsh:    ln -sf ~/tnotes/completions/_tn ~/.zsh/completions/_tn  # $fpath entry
tn path                             # prints store path; run once to confirm install
python -m pytest -q                 # optional sanity check (needs the install above first)
```

## Shell startup (optional, manual)

The conf.d hook shows notes on every directory change. For a show at shell
startup too, add this one-liner to `~/.config/fish/config.fish` by hand
(it is deliberately not scripted):

tn show --startup -l 2>/dev/null

## Usage (abridged)

tn "buy milk" | tn -g "pay bills" | tn --url URL --title T --tags a,b | tn --cmd "make test"
tn                      # picker here-only  tn --all # everywhere
tn list [--all] [-g|-l] [--done] [--hidden]
tn search Q [--all]     tn show [--startup] [-g|-l] [--done]
tn show ID [--preview]  tn open ID [n]  tn run ID [n]
tn edit ID | tn rm ID | tn done ID | tn undone ID | tn hide ID | tn unhide ID | tn path

Env: TNOTES_DIR, EDITOR/VISUAL, BROWSER, PAGER, NOTE_AUTOSHOW_GLOBAL=1.

## TUI keys

`tn tui` opens the persistent browser (mouse click/wheel work; narrow
windows stack panes via the compact layout). Entries are grouped by
directory — `enter`/click a folder to expand it, `backspace` (or the
`^ parent` button) to go up. Every keybar action is also a
clickable button; clicking a row selects it, clicking a dialog field focuses
it. Mouse needs terminal support — inside tmux set `set -g mouse on`.

| Key | Action |
|---|---|
| `j` / `k` | navigate entries |
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
