from textual.widgets import Markdown
from tnotes import store
from tnotes.tui import TnotesApp

def _seed(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="first", body="first-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    store.add_entry(type="note", title="second", body="second-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)

async def test_navigate_updates_preview(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_entry.title == "first"
        await pilot.press("j")
        await pilot.pause()
        assert app.current_entry.title == "second"
        assert "second-body" in app.preview_source

async def test_filter_narrows_list(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.click("#filter")  # focus; typing goes to Input
        await pilot.press(*"second")
        await pilot.pause()
        assert [e.title for e in app.shown] == ["second"]

async def test_compact_class_on_narrow(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    app = TnotesApp()
    async with app.run_test(size=(60, 24)) as pilot:
        await pilot.pause()
        assert app.has_class("compact")


from tnotes import store


async def _two(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="links", body="a https://a.example b https://b.example",
                    tags=[], scope="global", cwd=None, show_on_open=True)
    store.add_entry(type="note", title="plain", body="nothing", tags=[],
                    scope="global", cwd=None, show_on_open=True)

async def test_o_on_plain_does_nothing(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.press("j")  # select "plain"
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert app.current_entry.title == "plain"  # still here, no exit/crash

async def test_submenu_runs_second_action(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    import tnotes.tui as T
    picked = {}
    async def fake_run_worker(self, *a, **k):
        picked.update(k.get("marker", {}))
    monkeypatch.setattr(T.TnotesApp, "_run_open", lambda self, url: picked.update(url=url))
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()  # "links" selected
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("j", "enter")  # second URL
        await pilot.pause()
        assert picked.get("url") == "https://b.example"

async def test_done_toggle_refreshes(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert app.current_entry.status == "done"

async def test_enter_single_open_performs_directly(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="one", body="see https://a.example",
                    tags=[], scope="global", cwd=None, show_on_open=True)
    import tnotes.tui as T
    calls = {}
    monkeypatch.setattr(T.TnotesApp, "_run_open",
                        lambda self, url: calls.update(open=url))
    monkeypatch.setattr(T.TnotesApp, "_confirm_run",
                        lambda self, cmd: calls.update(run=cmd))
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert calls.get("open") == "https://a.example"
        assert len(app.screen_stack) == 1

async def test_enter_multi_opens_submenu(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    import tnotes.tui as T
    monkeypatch.setattr(T.TnotesApp, "_run_open", lambda self, url: None)
    monkeypatch.setattr(T.TnotesApp, "_confirm_run", lambda self, cmd: None)
    from tnotes.tui import TnotesApp, ActionMenuScreen
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_entry.title == "links"
        await pilot.press("enter")
        await pilot.pause()
        assert len(app.screen_stack) == 2
        assert isinstance(app.screen_stack[-1], ActionMenuScreen)

async def test_enter_plain_noop(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    import tnotes.tui as T
    calls = {}
    monkeypatch.setattr(T.TnotesApp, "_run_open",
                        lambda self, url: calls.update(open=url))
    monkeypatch.setattr(T.TnotesApp, "_confirm_run",
                        lambda self, cmd: calls.update(run=cmd))
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("j")  # select "plain"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert calls == {}
        assert len(app.screen_stack) == 1

async def test_mouse_works_with_empty_store(tmp_path, monkeypatch):
    """Regression: TnotesApp shadowed DOMNode.visible (bool) with a list of
    entries. An empty list is falsy, so the framework hit-tested the whole
    app as invisible and every mouse click died. No entries seeded here."""
    from textual.widgets import Input
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        found, _ = app.screen.get_widget_at(50, 5)
        assert found is not None
        await pilot.press("n")  # new-note dialog
        await pilot.pause()
        app.screen.refresh(layout=True)
        await pilot.pause()
        title = app.screen.query_one("#nt-title")
        r = title.region
        await pilot.click("#nt-title", offset=(r.width // 2, r.height // 2))
        await pilot.pause()
        assert app.screen.query_one("#nt-title", Input).has_focus

async def _click_center(pilot, app, selector):
    w = app.screen.query_one(selector)
    r = w.region
    await pilot.click(selector, offset=(r.width // 2, r.height // 2))

async def test_keybar_open_button_runs_first_link(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    import tnotes.tui as T
    picked = {}
    monkeypatch.setattr(T.TnotesApp, "_run_open",
                        lambda self, url: picked.update(url=url))
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()  # "links" selected: 2 opens, 0 runs
        assert app.screen.query_one("#kb-run").display is False
        await _click_center(pilot, app, "#kb-open")
        await pilot.pause()  # 2 links -> submenu; enter picks the first
        await pilot.press("enter")
        await pilot.pause()
        assert picked.get("url") == "https://a.example"

async def test_keybar_done_button_toggles_status(tmp_path, monkeypatch):
    await _two(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert app.current_entry.status == "active"
        await _click_center(pilot, app, "#kb-done")
        await pilot.pause()
        assert app.current_entry.status == "done"

async def test_click_row_selects_entry(tmp_path, monkeypatch):
    _seed(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_entry.title == "first"
        row = next(e for e in app.shown if e.title == "second")
        await _click_center(pilot, app, f"#row-{row.id}")
        await pilot.pause()
        assert app.current_entry.title == "second"

async def test_tui_open_detaches_browser_stdio(tmp_path, monkeypatch):
    """Opening a link must not let the browser's stdout scribble on the TUI."""
    await _two(tmp_path, monkeypatch)
    import tnotes.tui as T
    calls = {}
    def fake_open(url, **kwargs):
        calls.update(url=url, **kwargs)
        return 0
    monkeypatch.setattr(T.actions, "open_target", fake_open)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._run_open("https://a.example")
        await pilot.pause()
        await pilot.pause()
        assert calls.get("url") == "https://a.example"
        assert calls.get("quiet") is True

async def test_tui_run_cmd_reaches_backend(tmp_path, monkeypatch):
    """_run_cmd must reach run_command (headless takes the no-suspend path)."""
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    import tnotes.tui as T
    calls = {}
    monkeypatch.setattr(T.actions, "run_command",
                        lambda cmd, confirm=False: calls.update(cmd=cmd) or 0)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._run_cmd("echo hi")
        assert calls.get("cmd") == "echo hi"

def _seed_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    sub = tmp_path / "sub"
    sub.mkdir()
    store.add_entry(type="note", title="root-note", body="root-body", tags=[],
                    scope="local", cwd=str(tmp_path), show_on_open=True)
    store.add_entry(type="note", title="sub-note", body="sub-body", tags=[],
                    scope="local", cwd=str(sub), show_on_open=True)
    store.add_entry(type="note", title="g-note", body="g-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    return sub

def _labels(app):
    from textual.widgets import ListView
    lv = app.screen.query_one("#entries", ListView)
    return [str(item.query_one("Label").render()) for item in lv.children]

async def test_grouped_lists_dirs_collapsed(tmp_path, monkeypatch):
    _seed_tree(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp(root=str(tmp_path))
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        labels = _labels(app)
        assert any("Global (1)" in l for l in labels)
        assert any("sub (1)" in l for l in labels)
        assert not any("sub-body" in l for l in labels)  # collapsed: no entries

async def test_enter_expands_group_and_previews_summary(tmp_path, monkeypatch):
    _seed_tree(tmp_path, monkeypatch)
    from textual.widgets import ListView
    from tnotes.tui import TnotesApp
    app = TnotesApp(root=str(tmp_path))
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        labels = _labels(app)
        sub_idx = next(i for i, l in enumerate(labels) if "sub (1)" in l)
        app.screen.query_one("#entries", ListView).index = sub_idx
        await pilot.pause()
        await pilot.pause()  # row rebuild mounts new rows async
        assert any("sub-note" in l for l in _labels(app))
        assert "sub" in app.preview_source

async def test_backspace_roots_at_parent(tmp_path, monkeypatch):
    sub = _seed_tree(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp(root=str(sub))
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert app.root == str(sub)
        await pilot.press("backspace")
        await pilot.pause()
        assert app.root == str(tmp_path)

async def test_filter_auto_expands_hits(tmp_path, monkeypatch):
    _seed_tree(tmp_path, monkeypatch)
    from tnotes.tui import TnotesApp
    app = TnotesApp(root=str(tmp_path))
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await pilot.click("#filter")
        await pilot.press(*"sub-body")
        await pilot.pause()
        await pilot.pause()  # one rebuild per keystroke settles async
        assert any("sub-note" in l for l in _labels(app))
        assert not any("root-note" in l for l in _labels(app))

async def test_theme_header_and_rich_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    from textual.widgets import Label, Static
    from tnotes.tui import TnotesApp
    e = store.add_entry(type="url", title="tagged", body="https://x.example",
                        tags=["docs", "read"], scope="global", cwd=None,
                        show_on_open=True)
    app = TnotesApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert app.theme == "tnotes"
        header = str(app.screen.query_one("#header", Static).render())
        assert "tn" in header and "1 note" in header
        row = app.screen.query_one(f"#row-{e.id}")
        assert "tagged" in str(row.query_one(".row-main", Label).render())
        assert "#docs #read" in str(row.query_one(".row-tags", Label).render())
        assert e.id[:4] in str(row.query_one(".row-id", Label).render())


async def test_preview_keeps_multiline_body(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="multi", body="line one\nline two",
                    tags=[], scope="global", cwd=None, show_on_open=True)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert "line one  \nline two" in app.preview_source


async def test_in_place_editor_enter_inserts_newline(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="edit me", body="base", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        editor = app._editor
        assert editor is not None and editor.has_focus
        await pilot.press("A", "enter", "B")
        await pilot.pause()
        assert "\n" in editor.text


async def test_in_place_editor_enter_does_not_run_entry_action(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="link note", body="see https://x.example",
                    tags=[], scope="global", cwd=None, show_on_open=True)
    import tnotes.tui as T
    calls = {}
    monkeypatch.setattr(T.TnotesApp, "_run_open",
                        lambda self, url: calls.update(url=url))
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert calls == {}
        assert "\n" in app._editor.text


async def test_in_place_editor_saves_even_if_focus_moves(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="edit me", body="base", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        await pilot.press("X")
        app.query_one("#filter").focus()
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert app._editor is None
        assert "X" in store.get_entry(e.id).body


async def test_new_note_focuses_body_and_enter_adds_newline(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    from textual.widgets import TextArea
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        body = app.screen.query_one("#nt-body", TextArea)
        assert body.has_focus
        await pilot.press("A", "enter", "B")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert [x.body for x in store.load_all()] == ["A\nB"]


async def test_new_note_title_enter_moves_to_body(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    from textual.widgets import Input, TextArea
    from tnotes.tui import TnotesApp
    app = TnotesApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        title = app.screen.query_one("#nt-title", Input)
        title.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.query_one("#nt-body", TextArea).has_focus


async def test_confirm_dialog_yes_no_buttons(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="r", body="run `echo hi`", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    import tnotes.tui as T
    calls = {}
    monkeypatch.setattr(T.TnotesApp, "_run_cmd",
                        lambda self, cmd: calls.update(cmd=cmd))
    from tnotes.tui import TnotesApp, ConfirmScreen
    app = TnotesApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await pilot.press("r")  # single run action -> confirm dialog
        await pilot.pause()
        assert isinstance(app.screen_stack[-1], ConfirmScreen)
        await _click_center(pilot, app, "#confirm-no")
        await pilot.pause()
        assert calls == {}
        assert len(app.screen_stack) == 1
        await pilot.press("r")
        await pilot.pause()
        await _click_center(pilot, app, "#confirm-yes")
        await pilot.pause()
        assert calls.get("cmd") == "echo hi"
