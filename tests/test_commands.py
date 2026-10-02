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

def test_resolve_entry_numeric_here_only(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    def _ent(eid, title):
        return {"id": eid, "type": "note", "title": title, "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": "active",
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("aa000a", "first")) + "\n" +
        json.dumps(_ent("bb000b", "second")) + "\n", encoding="utf-8")
    assert commands.resolve_entry("1").id == "aa000a"
    assert commands.resolve_entry("2").id == "bb000b"
    with pytest.raises(EntryNotFound):
        commands.resolve_entry("9999999")

def test_resolve_entry_numeric_out_of_range_hints_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    commands.do_add(type="note", title="only", body="b", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    with pytest.raises(EntryNotFound, match="tn list"):
        commands.resolve_entry("9999999")

def test_resolve_entry_id_prefix_wins_over_number(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    def _ent(eid, title):
        return {"id": eid, "type": "note", "title": title, "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": "active",
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("bb000b", "first")) + "\n" +
        json.dumps(_ent("1a2b3c", "second")) + "\n", encoding="utf-8")
    assert commands.resolve_entry("1").id == "1a2b3c"

def test_done_number_matches_active_list(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    def _ent(eid, title, status):
        return {"id": eid, "type": "note", "title": title, "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": status,
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("aa000a", "old-done", "done")) + "\n" +
        json.dumps(_ent("bb000b", "still-here", "active")) + "\n", encoding="utf-8")
    assert commands.do_set_status("1", "done").id == "bb000b"

def test_undone_number_matches_done_list(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    def _ent(eid, title, status):
        return {"id": eid, "type": "note", "title": title, "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": status,
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("aa000a", "first-done", "done")) + "\n" +
        json.dumps(_ent("bb000b", "active", "active")) + "\n" +
        json.dumps(_ent("cc000c", "second-done", "done")) + "\n", encoding="utf-8")
    assert commands.do_set_status("2", "active").id == "cc000c"
