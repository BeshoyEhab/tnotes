# tnotes — terminal notepad with actions — Design Spec

Date: 2026-09-29
Status: approved (5/5 sections + rev1: per-dir scope, done/hide states)
Approach: A — JSONL + fzf picker (fresh repo, no compat)

## 1. Goal

Replace `~/.local/bin/note` (global + per-dir timestamped notes, fish autoshow)
with `tn` — a Python CLI in `~/tnotes` git repo that stores typed entries
(url, cmd, note, future types) and lets the user preview safely first,
then open / run / copy / edit from the terminal.

Keeps: global vs per-directory scope, per-dir autoshow on `cd`.
Adds: executable urls/cmds (incl. inline), big-note preview, done vs active,
show-on-open pinning.

Non-goals: full-screen TUI, multi-user sync, web UI, auto-migration command.

## 2. Entry syntax — how URLs / commands become executable

No `!` or `\` prefixes (collide with fish/bash history + escapes).
Type is explicit at add time; inline actions use markdown-native syntax
extracted at preview time, so literal `!` / `\` / `C:\path` stay plain text.

Quick-add (default type = note, default scope = local for CWD):

```bash
tn "buy milk"                                   # local note for $PWD
tn -g "pay bills"                               # global note (shown everywhere)
tn -l "per-dir only"                            # explicit local
tn --note "deploy steps" -m
tn --url https://docs.python.org --title "py docs" --tags py,read
tn --url https://x --title t -g                 # global url
tn --cmd "docker ps -a" --title "list containers" --tags docker
tn --cmd "make test" --no-show                  # hidden from dir-open autoshow
echo "pytest -q" | tn --cmd --title "quick test"
tn -m                  # compose note in $EDITOR
tn --url -m            # compose url entry (template with URL: field)
tn --cmd -m            # compose cmd entry (template with CMD: field)
tn edit <id>           # edit existing entry in $EDITOR
tn done <id>           # mark completed (hidden by default)
tn undone <id>         # back to active
tn hide <id>           # show_on_open=false (skip autoshow)
tn unhide <id>         # show_on_open=true
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

## 3. Big-note rendering + scope filtering — safe preview first

`tn` (no args) = picker defaulting to HERE ONLY:
`fzf --preview 'tn show {id} --preview' --preview-window=right:60%:wrap`
over `global(active) + local(active, cwd==$PWD)`. Flags: `tn --all` (all dirs),
`tn -g` (global only), `tn -l` (this dir only), `tn --done` (include completed),
`tn --hidden` (include show_on_open=false).

List row: `{icon} {title} [{tags}] {scope}` where icon = 🔗 url, `$` cmd, 📝 note,
scope = `G` global / `·` local; done entries show `✔` and are hidden unless `--done`/`--all --done`.

Preview pane (max 100 body lines):
```
🔗 py docs [py,read] (G) 2026-09-29
https://docs.python.org
cwd: - / status: active / show: yes
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
- `tn show` = global + this dir (active, show_on_open any). `tn show --startup`
  = same but silent when empty (fish hook). `tn show --startup -l` = this dir only.
  Completed (`status=done`) never shows in autoshow; `show_on_open=false` never
  shows in autoshow but still shows in manual `tn show` / picker.
- Store holds unlimited length; only preview truncates.

## 4. Storage + repo layout

Fresh `~/tnotes` git repo. Python 3.12+, stdlib-only runtime + external `fzf` binary.
Managed with `uv`. Installed as `tn` shim → `~/.local/bin/tn` symlink to repo.

```
~/tnotes/
  pyproject.toml
  src/tnotes/
    cli.py      # parsing, add/show/list/search/open/run/edit/rm/done/hide/path
    store.py    # JSONL load/append/edit, atomic temp+rename writes
    extract.py  # URL / cmd extraction per §2
    actions.py  # open (xdg-open/$BROWSER), run (confirm), copy (wl-copy/xclip/xsel), edit
    picker.py   # fzf wrapper (default here-only, --all for everywhere)
  tests/test_store.py, test_extract.py, test_cli.py
  README.md
```

Store: `~/.local/share/tnotes/tnotes.jsonl` (override `TNOTES_DIR`).
One JSON per line:

```json
{"id":"a3f9c1","type":"url","title":"py docs","body":"https://...","tags":["py","read"],"scope":"global","cwd":null,"status":"active","show_on_open":true,"created":"2026-09-29T18:00:00","updated":"2026-09-29T18:00:00"}
```

- `scope`: `global` | `local`. `cwd`: resolved absolute path for local, null for global.
- `status`: `active` | `done`. `show_on_open`: bool (autoshow pin).
- Defaults on add: `scope=local` (unless `-g`), `cwd=resolved $PWD` for local,
  `status=active`, `show_on_open=true` (unless `--no-show`).
- Atomic append via temp+rename; Ctrl-C safe.
- `type` is a plain string; new types need no migration.
- `id` = 6-char lowercase hex, unique; `tn show --startup` silent when empty;
  `tn show <id> --preview` prints capped 100-line preview for fzf.

CLI surface:

```bash
tn "text" [-g|-l] [--title --tags] [--no-show] [-m]
tn --url <u> / --cmd "<c>" [-g|-l] [...]
tn                       # picker here-only (global+this dir)
tn --all / tn -g / tn -l # picker scope variants
tn list [--all] [-g|-l] [--done] [--hidden]
tn search <q> [--all] [-g|-l] [--done]
tn show [--startup] [-g|-l] [--done]
tn show <id> [--preview]
tn open <id> [n]
tn run <id> [n]
tn edit <id> / tn rm <id> / tn done <id> / tn undone <id> / tn hide <id> / tn unhide <id> / tn path
```

## 5. Fish integration + future-proofing

- New `conf.d/tnotes-autoshow.fish`: on `PWD` change, once per shell per dir,
  run `tn show --startup -l` (this dir, active, show_on_open only; global skipped
  unless `NOTE_AUTOSHOW_GLOBAL=1` → plain `tn show --startup`). Mirrors old `note-autoshow.fish`.
- New `completions/tn.fish`, one startup line in `config.fish` (`tn show --startup`).
  Old `note` files left untouched until sunset.
- Future types = new `type` value only. Only `extract.py` learns new patterns.
- Env: `TNOTES_DIR`, `EDITOR`/`VISUAL`, `BROWSER`, `PAGER`.
  Clipboard: `wl-copy` → `xclip` → `xsel`. Opener: `xdg-open` → `$BROWSER`.

## 6. Errors, testing, sunset

Errors: failed writes preserve temp file; missing `fzf` falls back to `tn list`;
missing opener/clipboard prints content + path; `run` always asks `run? [y/N]`,
prints exit code, never auto-runs on preview.

Tests (`pytest`): store round-trip + atomicity + scope/cwd/status/show_on_open defaults;
extract (bare / `[label](url)` / `` `x` `` / fenced, `!` + `\` untouched);
CLI add/show/search + filters (`-g`/`-l`/`--all`/`--done`, autoshow hides done + hidden).

Sunset old `note` (single-user, agent does it, no import command in `tn`):
1. Build `tn` stable with its own store.
2. 1–2 weeks validation → agent one-off manual migration
   (`~/.local/share/mynotes/global.md` → global/active/show_on_open=true notes;
   `local/*.md` → local notes with cwd from old index.json), user verifies.
3. Delete `~/.local/bin/note`, `note-autoshow.fish`, `completions/note.fish`,
   startup block. Keep `~/.local/share/mynotes/` backup until user says delete.

## 7. Success criteria

- `tn --url/--cmd/--note [-g|-l]` + `tn -m` work; `!`/`\` never trigger actions.
- Picker defaults here-only; `tn --all` shows other dirs; `tn done/hide` + `--done`/`--hidden` work; autoshow shows this dir active + pinned only, silent when empty.
- `tn` picker previews with Actions list; `o`/`r`/`c`/`e`/`enter` work; big notes truncate at 100 + full in pager.
- `pytest` green. Fresh `~/tnotes` repo committed. Old `note` still works until sunset.
