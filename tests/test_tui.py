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
