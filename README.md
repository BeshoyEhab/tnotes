# tnotes — terminal notepad with actions

`tn` stores typed entries (url, cmd, note) in JSONL and previews safely first,
then open / run / copy / edit from the terminal.

## Install

uv sync
ln -sf ~/tnotes/.venv/bin/tn ~/.local/bin/tn   # or: pipx / uv tool install
mkdir -p ~/.config/fish/conf.d ~/.config/fish/completions
ln -sf ~/tnotes/fish/conf.d/tnotes-autoshow.fish ~/.config/fish/conf.d/
ln -sf ~/tnotes/fish/completions/tn.fish ~/.config/fish/completions/

Fallback without uv:

pip install -e .   # tests need the package installed: run `python -m pytest` only after `uv sync` or `pip install -e .`

Old `note` (~/.local/bin/note + fish hooks) keeps working until sunset — do not delete yet.

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
