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
        assert [e.title for e in app.visible] == ["second"]

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
