# tnotes — terminal notepad with actions — Design Spec

Date: 2026-09-29
Status: approved (5/5 sections)
Approach: A — JSONL + fzf picker (fresh repo, no compat)

## 1. Goal

Replace `~/.local/bin/note` (global + per-dir timestamped notes, fish autoshow)
with `tn` — a Python CLI in `~/tnotes` git repo that stores typed entries
(url, cmd, note, future types) and lets the user preview safely first,
then open / run / copy / edit from the terminal.

Non-goals: full-screen TUI, multi-user sync, web UI, auto-migration command.

## 2. Entry syntax — how URLs / commands become executable

No `!` or `\` prefixes (collide with fish/bash history + escapes).
Type is explicit at add time; inline actions use markdown-native syntax
extracted at preview time, so literal `!` / `\` / `C:\path` stay plain text.

Quick-add (default type = note):

```bash
tn "buy milk"
tn --note "deploy steps" -m
tn --url https://docs.python.org --title "py docs" --tags py,read
tn --cmd "docker ps -a" --title "list containers" --tags docker
echo "pytest -q" | tn --cmd --title "quick test"
tn -m                  # compose note in $EDITOR
tn --url -m            # compose url entry (template with URL: field)
tn --cmd -m            # compose cmd entry (template with CMD: field)
tn edit <id>           # edit existing entry in $EDITOR
```

Inline executables inside a normal note:

```bash
tn --note "check this [here is a link](https://example.com/guide) to continue, then run \`docker ps -a\`"
```

Extraction rules (`extract.py`):
- `[label](https://...)` → open-action for the URL
- bare `https?://...` → open-action (trailing punctuation stripped)
- `` `single cmd` `` → run-action
- ```` ```sh ... ``` ```` fenced blocks → one run-action per non-empty line
- Everything else is plain text, even if it contains `!`, `\`, `~`.

Editor-add flow:
- Temp file with `# ... ignored` header + draft, opened via `$EDITOR` → `$VISUAL` → `vi`.
- Save+quit = one JSONL entry. Empty / all-comments = discarded.
- Failed write keeps temp path in error message; nothing is lost.

## 3. Big-note rendering — safe preview first

`tn` (no args) = `fzf --preview 'tn show {id} --preview' --preview-window=right:60%:wrap`.
List row: `{icon} {title} [{tags}]` where icon = 🔗 url, `$` cmd, 📝 note.

Preview pane (max 100 body lines):
```
🔗 py docs [py,read] 2026-09-29
https://docs.python.org
---
Actions:
 [o1] open https://docs.python.org
 [c] copy  [e] edit  [enter] full view
---
Body (wrapped):
...
… (+240 lines, Enter for full)
```

- Renderer: `bat -p` if present, else plain wrapped text.
- Scroll preview with Shift-Up/Down. `enter` = full body in `$PAGER` (`less -R`).
- Keys: `enter` full, `o` open, `r` run (always confirms), `c` copy, `e` edit, `q` quit.
- Store holds unlimited length; only preview truncates.

## 4. Storage + repo layout

Fresh `~/tnotes` git repo. Python 3.12+, stdlib-only runtime + external `fzf` binary.
Managed with `uv`. Installed as `tn` shim → `~/.local/bin/tn` symlink to repo.

```
~/tnotes/
  pyproject.toml
  src/tnotes/
    cli.py      # parsing, add/show/list/search/open/run/edit/rm/path
    store.py    # JSONL load/append/edit, atomic temp+rename writes
    extract.py  # URL / cmd extraction per §2
    actions.py  # open (xdg-open/$BROWSER), run (confirm), copy (wl-copy/xclip/xsel), edit
    picker.py   # fzf wrapper
  tests/test_store.py, test_extract.py, test_cli.py
  README.md
```

Store: `~/.local/share/tnotes/tnotes.jsonl` (override `TNOTES_DIR`).
One JSON per line:

```json
{"id":"a3f9c1","type":"url","title":"py docs","body":"https://...","tags":["py","read"],"created":"2026-09-29T18:00:00","updated":"2026-09-29T18:00:00"}
```

- Atomic append via temp+rename; Ctrl-C safe.
- `type` is a plain string; new types need no migration.
- `id` = 6-char lowercase hex, unique; `tn show --startup` is silent when store is empty (for fish hooks); `tn show <id> --preview` prints the capped 100-line preview used by fzf.

CLI surface:

```bash
tn "text" / tn --url <u> / tn --cmd "<c>" [--title --tags] [-m]
tn                       # picker
tn list / tn search <q> / tn show <id> [--preview]
tn open <id> [n]
tn run <id> [n]
tn edit <id> / tn rm <id> / tn path
```

## 5. Fish integration + future-proofing

- New `conf.d/tnotes-autoshow.fish` (silent `tn show --startup` on `cd`), new
  `completions/tn.fish`, one startup line in `config.fish`. Old `note` files
  left untouched until sunset.
- Future types = new `type` value only. Only `extract.py` learns new patterns.
- Env: `TNOTES_DIR`, `EDITOR`/`VISUAL`, `BROWSER`, `PAGER`.
  Clipboard: `wl-copy` → `xclip` → `xsel`. Opener: `xdg-open` → `$BROWSER`.

## 6. Errors, testing, sunset

Errors: failed writes preserve temp file; missing `fzf` falls back to `tn list`;
missing opener/clipboard prints content + path; `run` always asks `run? [y/N]`,
prints exit code, never auto-runs on preview.

Tests (`pytest`): store round-trip + atomicity, extract (bare / `[label](url)` /
`` `x` `` / fenced, `!` + `\` untouched), CLI add/show/search.

Sunset old `note` (single-user, agent does it, no import command in `tn`):
1. Build `tn` stable with its own store.
2. 1–2 weeks validation → agent one-off manual migration
   (`~/.local/share/mynotes/*.md` → `tnotes.jsonl` as notes), user verifies.
3. Delete `~/.local/bin/note`, `note-autoshow.fish`, `completions/note.fish`,
   startup block. Keep `~/.local/share/mynotes/` backup until user says delete.

## 7. Success criteria

- `tn --url/--cmd/--note` + `tn -m` work; `!`/`\` in text never trigger actions.
- `tn` picker previews with Actions list; `o`/`r`/`c`/`e`/`enter` work; big notes truncate at 100 + full in pager.
- `pytest` green. Fresh `~/tnotes` repo committed. Old `note` still works until sunset.
