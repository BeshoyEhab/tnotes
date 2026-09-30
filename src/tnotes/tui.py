"""Persistent textual TUI. Browse shell in this task; actions in the next."""
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, ListItem, ListView, Markdown, Static
from . import commands
from .models import Entry
from .picker import format_row

class EntrySelected(Message):
    def __init__(self, entry: Entry | None) -> None:
        super().__init__()
        self.entry = entry

class TnotesApp(App):
    CSS_PATH = "tnotes.css"
    BINDINGS = [("q", "quit", "quit"), ("/", "focus_filter", "filter"),
                ("j", "move_down", "down"), ("k", "move_up", "up")]

    def __init__(self, scope: str = "here", all_dirs: bool = False,
                 include_done: bool = False) -> None:
        super().__init__()
        self.scope = scope
        self.all_dirs = all_dirs
        self.include_done = include_done
        self.entries: list[Entry] = []
        self.visible: list[Entry] = []
        self.query: str = ""
        self.current_entry: Entry | None = None
        self.preview_source: str = ""
        self.keybar_plain: str = ""

    @property
    def visible(self) -> list[Entry]:
        """Filtered entries for the list pane.

        Shadows DOMNode.visible (a bool widget-visibility flag): the TUI
        never toggles app-level visibility, so this seam owns the name.
        """
        return self.__dict__.get("_visible_entries", [])

    @visible.setter
    def visible(self, value: list[Entry] | bool) -> None:
        if isinstance(value, bool):
            # Framework-style visibility set; keep base-class behavior.
            self.styles.visibility = "visible" if value else "hidden"
        else:
            self.__dict__["_visible_entries"] = value

    def compose(self) -> ComposeResult:
        yield Input(placeholder="filter…", id="filter")
        with Horizontal(id="body"):
            yield ListView(id="entries")
            yield Markdown(id="preview")
        yield Static(id="keybar")

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
            same = [e for e in self.visible if e.id == keep]
            self.select_entry(same[0] if same else (self.visible[0] if self.visible else None))
        else:
            self.select_entry(self.visible[0] if self.visible else None)

    def apply_filter(self) -> None:
        q = self.query.lower()
        self.visible = [e for e in self.entries
                        if not q or q in (e.title + "\n" + e.body).lower()]
        self._rebuild_rows()
        if self.current_entry and self.current_entry.id not in {e.id for e in self.visible}:
            self.select_entry(self.visible[0] if self.visible else None)

    def _rebuild_rows(self) -> None:
        """Sync ListView rows with self.visible.

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
                for e in self.visible]

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
        idx = next((i for i, e in enumerate(self.visible)
                    if e.id == self.current_entry.id), None)
        if idx is not None and idx < len(lv):
            lv.index = idx

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self.visible):
            self.select_entry(self.visible[idx])

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

    def update_keybar(self) -> None:
        # Task 5 makes this dynamic via selection_actions; static superset now.
        plain = "j/k navigate · / filter · n new · q quit"
        self.keybar_plain = plain
        self.query_one("#keybar", Static).update(plain)

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < 90, "compact")

    async def on_input_changed(self, event: Input.Changed) -> None:
        self.query = event.value
        self.apply_filter()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_move_down(self) -> None:
        self.query_one("#entries", ListView).action_cursor_down()

    def action_move_up(self) -> None:
        self.query_one("#entries", ListView).action_cursor_up()
