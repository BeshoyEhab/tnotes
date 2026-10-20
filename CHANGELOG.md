# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Apply the gruvbox-bright palette to CLI rows and the TUI; quieter borderless layout.
- Fix TUI editing: `enter` inserts newlines and new notes focus the body, so `ctrl-s` saves the edit instead of triggering an entry action.
- Keep single line breaks in TUI and CLI Markdown previews instead of collapsing notes into one line.
- `tn done|undone|rm|hide|unhide` with no argument opens a picker.
- Fix shell completions to offer list row numbers instead of entry ids.
- Sunset legacy `note` shim references; `tn` is the supported entrypoint.
- Add bash/zsh completions alongside fish.
- Clean stale task-plan comments in `cli`/`commands`.
- Fix README dependency note (stdlib + `textual` for TUI).
- Add MIT LICENSE, CI workflow, gitignore coverage for `.pytest_cache/` and `.benchmarks/`.

## [0.1.0] - 2026-09-30

- Terminal notepad with actions: typed entries (url, cmd, note) in JSONL.
- CLI: quick-add, list/search/show, open/run/copy/edit, done/hide state commands.
- Pickers: `fzf` picker with preview keys; `textual` TUI browser.
- Fish autoshow hook + completions.
