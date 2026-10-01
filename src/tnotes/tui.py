"""Persistent textual TUI. Browse shell in this task; actions in the next."""
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Markdown, Static, TextArea
from . import actions, commands
from .extract import extract_actions
from .models import Entry
from .picker import format_row


def selection_actions(entry: Entry | None) -> dict:
    if entry is None:
        return {"opens": [], "runs": []}
    acts = extract_actions(entry)
    return {"opens": [a["target"] for a in acts if a["kind"] == "open"],
            "runs": [a["target"] for a in acts if a["kind"] == "run"]}


class ActionMenuScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "close"),
                ("j", "cursor_down", "down"),
                ("k", "cursor_up", "up")]

    def __init__(self, title: str, items: list[str]) -> None:
        super().__init__()
        self._title = title
        self._items = items

    def compose(self) -> ComposeResult:
        yield Label(self._title)
        yield ListView(*[ListItem(Label(t)) for t in self._items], id="menu")

    def on_mount(self) -> None:
        self.query_one("#menu", ListView).focus()

    def action_cursor_down(self) -> None:
        self.query_one("#menu", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#menu", ListView).action_cursor_up()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.list_view.index)


class ConfirmScreen(ModalScreen):
    BINDINGS = [("y", "confirm", "yes"), ("n", "dismiss", "no"),
                ("escape", "dismiss", "no")]

    def __init__(self, cmd: str) -> None:
        super().__init__()
        self._cmd = cmd

    def compose(self) -> ComposeResult:
        yield Label(f"run? [y/N]\n{self._cmd}")

    def action_confirm(self) -> None:
        self.dismiss(True)


class NewNoteScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "cancel"), ("ctrl+s", "save", "save")]

    def compose(self) -> ComposeResult:
        yield Label("new note (ctrl-s save, esc cancel)")
        yield Input(placeholder="title (optional)", id="nt-title")
        yield TextArea(id="nt-body")

    def action_save(self) -> None:
        title = self.query_one("#nt-title", Input).value
        body = self.query_one("#nt-body", TextArea).text
        self.dismiss((title, body))


class EntrySelected(Message):
    def __init__(self, entry: Entry | None) -> None:
        super().__init__()
        self.entry = entry

class TnotesApp(App):
    CSS_PATH = "tnotes.css"
    BINDINGS = [("q", "quit", "quit"), ("/", "focus_filter", "filter"),
                ("j", "move_down", "down"), ("k", "move_up", "up"),
                ("o", "open_link", "open"), ("r", "run_cmd", "run"),
                ("c", "copy_body", "copy"), ("d", "toggle_done", "done"),
                ("h", "toggle_hide", "hide"), ("n", "new_note", "new"),
                ("e", "edit_here", "edit"), ("E", "edit_external", "editor"),
                # priority: ListView binds enter to select_cursor; without
                # priority the app-level primary would never fire when the
                # entries list has focus. check_action disables primary on
                # modal screens so submenu/confirm enter still works.
                Binding("enter", "primary", "act", priority=True)]

    def __init__(self, scope: str = "here", all_dirs: bool = False,
                 include_done: bool = False) -> None:
        super().__init__()
        self.scope = scope
        self.all_dirs = all_dirs
        self.include_done = include_done
        self.entries: list[Entry] = []
        self.shown: list[Entry] = []
        self.query: str = ""
        self.current_entry: Entry | None = None
        self.preview_source: str = ""
        self.keybar_plain: str = ""
        self._editing: Entry | None = None
        self._editor: TextArea | None = None

    def compose(self) -> ComposeResult:
        yield Input(placeholder="filter…", id="filter")
        with Horizontal(id="body"):
            yield ListView(id="entries")
            yield Markdown(id="preview")
        with Horizontal(id="keybar"):
            yield Button("/ filter", id="kb-filter", compact=True)
            yield Button("o open", id="kb-open", compact=True)
            yield Button("r run", id="kb-run", compact=True)
            yield Button("c copy", id="kb-copy", compact=True)
            yield Button("e edit", id="kb-edit", compact=True)
            yield Button("d done", id="kb-done", compact=True)
            yield Button("h hide", id="kb-hide", compact=True)
            yield Button("n new", id="kb-new", compact=True)
            yield Button("q quit", id="kb-quit", compact=True)

    async def on_mount(self) -> None:
        self.refresh_entries()
        self.update_keybar()
        # Input auto-focuses on mount; steal it so j/k navigate, not type.
        self.query_one("#entries", ListView).focus()

    def refresh_entries(self, keep_selection: bool = True) -> None:
        keep = self.current_entry.id if (keep_selection and self.current_entry) else None
        self.entries = commands.do_list(scope=self.scope, include_done=self.include_done,
                                        all_dirs=self.all_dirs)
        self.apply_filter()
        if keep:
            same = [e for e in self.shown if e.id == keep]
            self.select_entry(same[0] if same else (self.shown[0] if self.shown else None))
        else:
            self.select_entry(self.shown[0] if self.shown else None)

    def apply_filter(self) -> None:
        q = self.query.lower()
        self.shown = [e for e in self.entries
                        if not q or q in (e.title + "\n" + e.body).lower()]
        self._rebuild_rows()
        if self.current_entry and self.current_entry.id not in {e.id for e in self.shown}:
            self.select_entry(self.shown[0] if self.shown else None)

    def _rebuild_rows(self) -> None:
        """Sync ListView rows with self.shown.

        Row removal/mounting is async; run it in an exclusive worker so
        rapid filter keystrokes cannot interleave a clear with a stale
        re-add of the same row ids (DuplicateIds). The worker re-syncs
        the highlight when done.
        """
        try:
            lv = self.query_one("#entries", ListView)
        except Exception:
            return
        rows = [ListItem(Label(format_row(e)), id=f"row-{e.id}")
                for e in self.shown]

        async def _do() -> None:
            await lv.clear()
            if rows:
                await lv.extend(rows)
            self._sync_list_highlight()

        self.run_worker(_do(), name="rebuild-rows", group="tnotes-list",
                        exclusive=True, exit_on_error=False)

    def select_entry(self, entry: Entry | None) -> None:
        self.current_entry = entry
        self.post_message(EntrySelected(entry))
        self._sync_list_highlight()

    def _sync_list_highlight(self) -> None:
        """Mirror current_entry onto ListView.index so j/k move relative to it.

        No-op while a rebuild worker is still mounting rows; the worker
        calls this again on completion.
        """
        try:
            lv = self.query_one("#entries", ListView)
        except Exception:
            return
        if self.current_entry is None:
            return
        idx = next((i for i, e in enumerate(self.shown)
                    if e.id == self.current_entry.id), None)
        if idx is not None and idx < len(lv):
            lv.index = idx

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id != "entries":
            return
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self.shown):
            self.select_entry(self.shown[idx])

    async def on_entry_selected(self, message: EntrySelected) -> None:
        src = self.preview_markdown(message.entry)
        self.preview_source = src
        await self.query_one("#preview", Markdown).update(src)
        self.update_keybar()

    @staticmethod
    def preview_markdown(entry: Entry | None) -> str:
        if entry is None:
            return "_No notes here yet — press `n` to add one._"
        head = f"## {entry.title or '(untitled)'}"
        meta = (f"{entry.type} · {entry.scope} · {entry.status} · "
                f"{'shown' if entry.show_on_open else 'hidden'}")
        tags = f"🏷️ {', '.join(entry.tags)}" if entry.tags else ""
        return "\n\n".join(p for p in [head, meta, tags, entry.body] if p)

    _KB_ACTIONS = {"kb-filter": "focus_filter", "kb-open": "open_link",
                   "kb-run": "run_cmd", "kb-copy": "copy_body",
                   "kb-edit": "edit_here", "kb-done": "toggle_done",
                   "kb-hide": "toggle_hide", "kb-new": "new_note"}

    def update_keybar(self) -> None:
        acts = selection_actions(self.current_entry)
        parts = [("j/k", "navigate"), ("/", "filter")]
        if acts["opens"]:
            parts.append(("o", f"open×{len(acts['opens'])}"))
        if acts["runs"]:
            parts.append(("r", f"run×{len(acts['runs'])}"))
        parts += [("c", "copy"), ("e", "edit"), ("d", "done"),
                  ("h", "hide"), ("n", "new"), ("q", "quit")]
        self.keybar_plain = " · ".join(f"{k} {v}" for k, v in parts)
        try:
            bar = self.query_one("#keybar", Horizontal)
        except Exception:
            return  # pre-mount (tests poking logic without compose)
        bar.query_one("#kb-open", Button).display = bool(acts["opens"])
        bar.query_one("#kb-run", Button).display = bool(acts["runs"])
        if acts["opens"]:
            bar.query_one("#kb-open", Button).label = f"o open×{len(acts['opens'])}"
        if acts["runs"]:
            bar.query_one("#kb-run", Button).label = f"r run×{len(acts['runs'])}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = self._KB_ACTIONS.get(event.button.id or "")
        if action == "focus_filter":
            self.action_focus_filter()
        elif action == "open_link":
            self.action_open_link()
        elif action == "run_cmd":
            self.action_run_cmd()
        elif action == "copy_body":
            self.action_copy_body()
        elif action == "edit_here":
            self.action_edit_here()
        elif action == "toggle_done":
            self.action_toggle_done()
        elif action == "toggle_hide":
            self.action_toggle_hide()
        elif action == "new_note":
            self.action_new_note()
        elif event.button.id == "kb-quit":
            self.exit()

    def check_action(self, action: str, parameters) -> bool | None:
        if action == "primary" and isinstance(self.screen, ModalScreen):
            return False
        if self.current_entry is None and action in (
                "open_link", "run_cmd", "copy_body", "edit_here",
                "toggle_done", "toggle_hide"):
            return False
        acts = selection_actions(self.current_entry)
        if action == "open_link" and not acts["opens"]:
            return False
        if action == "run_cmd" and not acts["runs"]:
            return False
        return True

    def _primary(self) -> tuple[str, str] | None:
        acts = selection_actions(self.current_entry)
        if acts["opens"]:
            return ("open", acts["opens"][0])
        if acts["runs"]:
            return ("run", acts["runs"][0])
        return None

    def action_open_link(self) -> None:
        acts = selection_actions(self.current_entry)["opens"]
        if len(acts) == 1:
            self._run_open(acts[0])
        elif acts:
            self.push_screen(ActionMenuScreen("open…", acts), self._menu_opened)

    def _menu_opened(self, idx: int | None) -> None:
        acts = selection_actions(self.current_entry)["opens"]
        if idx is None or not 0 <= idx < len(acts):
            return
        self._run_open(acts[idx])

    def _run_open(self, url: str) -> None:
        self.run_worker(lambda: actions.open_target(url), thread=True,
                        description=f"open {url}")
        self.notify(f"opening {url}")

    def action_run_cmd(self) -> None:
        acts = selection_actions(self.current_entry)["runs"]
        if len(acts) == 1:
            self._confirm_run(acts[0])
        elif acts:
            self.push_screen(ActionMenuScreen("run…", acts), self._menu_run)

    def _menu_run(self, idx: int | None) -> None:
        acts = selection_actions(self.current_entry)["runs"]
        if idx is None or not 0 <= idx < len(acts):
            return
        self._confirm_run(acts[idx])

    def _confirm_run(self, cmd: str) -> None:
        self.push_screen(ConfirmScreen(cmd), lambda yes: yes and self._run_cmd(cmd))

    def action_primary(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        acts = selection_actions(self.current_entry)
        opens = acts["opens"]
        runs = acts["runs"]
        total = len(opens) + len(runs)
        if total > 1:
            items = [f"open {u}" for u in opens] + [f"run {c}" for c in runs]
            self.push_screen(ActionMenuScreen("act…", items), self._menu_primary)
        elif total == 1:
            if opens:
                self._run_open(opens[0])
            else:
                self._confirm_run(runs[0])

    def _menu_primary(self, idx: int | None) -> None:
        acts = selection_actions(self.current_entry)
        items = ([f"open {u}" for u in acts["opens"]]
                 + [f"run {c}" for c in acts["runs"]])
        if idx is None or not 0 <= idx < len(items):
            return
        label = items[idx]
        if label.startswith("open "):
            self._run_open(label[len("open "):])
        elif label.startswith("run "):
            self._confirm_run(label[len("run "):])

    def _run_cmd(self, cmd: str) -> None:
        def go():
            rc = actions.run_command(cmd, confirm=False)
            self.call_from_thread(self.notify, f"exit: {rc}")
        self.run_worker(go, thread=True, description=f"run {cmd}")

    def action_copy_body(self) -> None:
        if self.current_entry:
            body = self.current_entry.body
            self.run_worker(lambda: actions.copy_text(body), thread=True)
            self.notify("copied")

    def action_toggle_done(self) -> None:
        if self.current_entry:
            e = self.current_entry
            updated = commands.do_set_status(e.id, "done" if e.status == "active" else "active")
            self.refresh_entries()
            if updated.id not in {x.id for x in self.shown}:
                self.select_entry(updated)

    def action_toggle_hide(self) -> None:
        if self.current_entry:
            e = self.current_entry
            commands.do_set_show(e.id, not e.show_on_open)
            self.refresh_entries()

    def action_edit_here(self) -> None:
        if not self.current_entry:
            return
        self._editing = self.current_entry
        preview = self.query_one("#preview")
        self._editor = TextArea(self.current_entry.body, id="editor")
        self.query_one("#body", Horizontal).mount(self._editor, after=preview)
        preview.display = False
        self._editor.focus()

    async def on_key(self, event: events.Key) -> None:
        if getattr(self, "_editor", None) is not None and self._editor.has_focus:
            if event.key == "ctrl+s":
                event.prevent_default()
                self._save_edit()
            elif event.key == "escape":
                event.prevent_default()
                self._cancel_edit()

    def _save_edit(self) -> None:
        body = self._editor.text.strip()
        if body:
            commands.do_set_body(self._editing.id, body)
        self._close_editor()

    def _cancel_edit(self) -> None:
        self._close_editor()

    def _close_editor(self) -> None:
        self.query_one("#preview").display = True
        self._editor.remove()
        self._editor = None
        self.refresh_entries()

    def action_new_note(self) -> None:
        self.push_screen(NewNoteScreen(), self._new_saved)

    def _new_saved(self, data: tuple[str, str] | None) -> None:
        if not data:
            return
        title, body = data
        if not body.strip():
            self.notify("discarded (empty)", severity="warning")
            return
        import os
        commands.do_add(type="note", title=title or body.splitlines()[0][:60],
                        body=body.strip(), tags=[], scope="local",
                        cwd=os.path.realpath(os.getcwd()), show_on_open=True)
        self.refresh_entries(keep_selection=False)

    def action_edit_external(self) -> None:
        if not self.current_entry:
            return
        entry = self.current_entry
        with self.suspend():
            text = commands.compose_text(entry.type, initial=entry.body)
        if text and text.strip() and text.strip() != entry.body:
            commands.do_set_body(entry.id, text.strip())
        self.refresh_entries()

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < 90, "compact")

    async def on_input_changed(self, event: Input.Changed) -> None:
        self.query = event.value
        self.apply_filter()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_move_down(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.query_one("#entries", ListView).action_cursor_down()

    def action_move_up(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.query_one("#entries", ListView).action_cursor_up()
