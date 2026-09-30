# tests/test_commands.py
import pytest
from tnotes import commands, store
from tnotes.models import EntryNotFound, NoActionError

def test_do_add_and_resolve(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="t", body="b", tags=["x"],
                        scope="global", cwd=None, show_on_open=True)
    assert isinstance(e, store.Entry) or hasattr(e, "id")
    assert commands.resolve_entry(e.id).id == e.id
    with pytest.raises(EntryNotFound):
        commands.resolve_entry("ffffff")

def test_do_open_picks_nth(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="n",
                        body="see https://a.example and https://b.example",
                        tags=[], scope="global", cwd=None, show_on_open=True)
    entry, url = commands.do_open(e.id, 2)
    assert url == "https://b.example"
    with pytest.raises(NoActionError):
        commands.do_run(e.id, 1)  # no run actions here

def test_do_remove_status_show(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = commands.do_add(type="note", title="t", body="b", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert commands.do_set_status(e.id, "done").status == "done"
    assert commands.do_set_show(e.id, False).show_on_open is False
    assert commands.do_remove(e.id) is True
    with pytest.raises(EntryNotFound):
        commands.resolve_entry(e.id)
