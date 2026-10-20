# tnotes polish — colors, CLI rows, TUI direction B

Approved 2026-10-20. Direction B (quiet, borderless) plus the no-arg picker.

## Tasks

- [x] Completion bug: row numbers as completion values (fish/bash/zsh)
- [x] Shared gruvbox-bright palette + type icons
- [x] CLI rows: dim number, colored type glyph, `#tags`, quiet id
- [x] Startup greeting uses the same row renderer
- [x] `tn done|undone|rm|hide|unhide` with no arg opens the picker
- [x] TUI: custom `tnotes` theme, header, borderless panes, rich rows, keybar
- [x] Final: full suite, reinstall completions, manual smoke test

## Notes

- Palette comes from `~/.config/starship.toml` (`gruvbox_bright`).
- Keep one `· id` tail so the completion parsers keep working.
- Keep `✔` as the done marker (already parsed by completions).
- No fills in the TUI except the selected-row state.
