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
