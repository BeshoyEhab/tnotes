# tnotes textual TUI — Design Spec

Date: 2026-09-30
Status: draft (pending user review)
Supersedes (UI layer only): `docs/superpowers/specs/2026-09-29-tnotes-design.md`
§2–§4 (entry syntax, preview format, storage schema/CLI surface, fish integration).
This spec replaces the fzf picker + `--preview` rendering path and hardens the
core underneath it. Everything else in the 09-29 spec stays in force, except
the stdlib-only runtime rule, which is amended below.

## 1. Goal

Replace the one-shot fzf picker with a persistent textual TUI (`tn` with no
args on a tty): filterable list + live markdown preview + footer key bar, with
mouse, responsive layout, in-place editing, and a multi-action picker. Stay in
the app after every action; inapplicable keys never appear, so they can't error.

Non-goals: web UI, multi-user sync, clickable footer, right-click menus,
changing the JSONL schema or the non-interactive CLI surface.

## 2. Architecture

New modules (all under `src/tnotes/`):

| Module | Responsibility |
|---|---|
| `models.py` | `Entry` dataclass: all 11 fields (`id type title body tags scope cwd status show_on_open created updated`), `from_dict`/`to_dict`, validation (`scope ∈ {global,local}`, `status ∈ {active,done}`, id 6-hex). Sole schema definition. `SCHEMA_VERSION = 2` with a migration hook (`migrate(doc) -> doc`) for future fields. |
| `config.py` | Central env resolution: `TNOTES_DIR` (default `~/.local/share/tnotes`), `EDITOR`→`VISUAL`→`vi`, `BROWSER`, `PAGER`, `NOTE_AUTOSHOW_GLOBAL`. One place, defaults documented, trivially monkeypatchable. |
| `store.py` (harden) | Return/accept `Entry` objects at the boundary (JSONL lines unchanged). `fcntl.flock(LOCK_EX)` around read-modify-write. Keep: atomic temp+rename, exact-first/ambiguous-prefix match, corrupt-line skip+warn. |
| `commands.py` (new) | Pure command functions (`do_add`, `do_done`, …) taking explicit args, called by both `cli.py` and `tui.py`. Eliminates the `cli`/`cli_read`/`cli_actions` lazy-import cycle; those modules become thin parsers/dispatchers. |
| `tui.py` (new) | `TnotesApp(App)` + widgets + `selection_actions(entry)` + UI action bridge. Styles in `tnotes.css`, never inline. |
| `picker.py` (keep) | Fallback only: used when `textual` is not importable. |

Dependency direction (no cycles, no lazy imports):
`models` ← `config`, `store` ← `extract`, `actions` ← `commands` ← `cli*`, `tui`.

Runtime dependency (spec amendment): `textual` (pinned minor in `pyproject.toml`,
`uv.lock` updated). The 09-29 "stdlib-only + fzf binary" rule becomes:
"stdlib-only core; `textual` for the TUI, `fzf` as TUI fallback."
Rationale (user-approved): curses would slow all future UI work; single-user
tool, network-at-install is acceptable.

Entry rule: bare `tn` launches the TUI only when stdin **and** stdout are ttys.
Pipes (`echo x | tn --cmd`), non-tty, or missing `textual` keep current behavior
(fzf picker → `tn list` fallback). Scope flags (`--all/-g/-l/--done`) seed the
app's initial filter.

## 3. TUI structure

```
┌ Filter input ─────────────────────────┐
│ List (1/3)      │ Markdown preview    │
│                 │ (2/3, scrollable)   │
├ Footer: key bar ──────────────────────┤
```

- Widgets: `Input` (filter), `ListView` (rows reuse `format_row` text),
  textual `Markdown` viewer, `Footer`-style custom key bar (footer must show
  only applicable keys — custom bar, not auto `Footer`).
- Panes communicate via `Message`s (`EntrySelected` list → preview).
  No direct widget-to-widget calls.
- State as reactives: `entries: list[Entry]`, `selected_id`, scope, query.
  `refresh_entries(keep_selection=True)` re-reads the store after every
  mutation, restores selection by id (fallback: same index).
- Single source of truth: `selection_actions(entry) -> {opens: [...],
  runs: [...], can_edit: True, ...}` derived from `extract_actions`. Keys,
  footer bar, and submenu all render from it.
- UI never calls blocking `actions.py` directly. Bridge: `run` → confirm
  modal → background worker → toast with exit code; `edit`/new-note dialog →
  suspend app → `$EDITOR` → resume + `refresh_entries`; `open`/`copy` →
  workers + toasts.
- `compact` responsive class via size watcher (width < 90): panes stack,
  footer shows key letters only.

## 4. Interaction

Keys (each disabled unless `selection_actions` allows it):
`j/k`/arrows navigate · `/` filter · `enter` primary (first open, else first
run, else nothing) · `o`/`r` action submenu (skipped when exactly one action;
`r` always via confirm modal) · `c` copy body · `d` toggle done ·
`h` toggle hide · `n` new-note dialog (title + body) · `e` in-place edit
(preview swaps to `TextArea`; `ctrl-s` saves via `store.update_entry`,
`esc` cancels) · `q`/`esc` quit (`esc` unwinds submenu → filter → quit).

Mouse: click row selects, wheel scrolls preview (native textual, no code).
Footer is display-only.

Multi-action submenu: modal list (`open <url>` / `run <cmd>` rows); `enter`
executes the highlighted row; `esc` closes. Used whenever an entry has >1
action of the pressed kind, and by `enter` when total actions >1.

Preview is dynamic: selection change and post-mutation refresh both re-render.

## 5. Errors, testing, install

- Errors: worker failures toast + log, never traceback; ambiguous ids reuse
  store errors surfaced as toasts; editor non-zero exit keeps draft (existing
  rule) and resumes the app; corrupt store lines warn once per load.
- Tests (`pytest`): unit — `Entry` validation/migration, `selection_actions`
  matrix (url/cmd/note × 0/1/N actions), `refresh_entries` selection restore,
  config defaults; UI — textual `Pilot` (`run_test()`): navigate→preview
  updates, `o` on no-URL entry does nothing, submenu picks 2nd action,
  in-place edit save/cancel, `ctrl-n`-equivalent `n` dialog, compact class
  under width 90, done-toggle refresh. Headless CI gets unit + Pilot only;
  one manual visual pass (colors, mouse, suspend-edit) by the user.
- Install delta (README): `uv sync` pulls `textual`; fallback chain
  textual → fzf → list documented; requirements table gains `textual`
  (required for TUI) and demotes `fzf` to TUI-fallback.

## 6. Success criteria

- `tn` stays open across open/run/copy/edit/done/hide/new; `q`/`esc` quits.
- Footer shows only applicable keys; narrow terminal compacts; preview
  follows selection and refreshes after mutations.
- Multi-URL/cmd entries offer a chooser; single-action entries act directly.
- Mouse click selects, wheel scrolls. No traceback reachable from any key.
- `pytest` green (unit + Pilot). Old fzf path intact as fallback. No JSONL
  schema change; non-interactive CLI byte-identical.
