# tests/test_store.py
import json, os
from pathlib import Path
from tnotes import store

def test_add_entry_defaults_local_active_shown(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="buy milk", body="buy milk",
                        tags=[], scope="local", cwd="/tmp/x", show_on_open=True)
    assert len(e["id"]) == 6 and all(c in "0123456789abcdef" for c in e["id"])
    assert e["scope"] == "local" and e["cwd"] == "/tmp/x"
    assert e["status"] == "active" and e["show_on_open"] is True
    assert "created" in e and "updated" in e
    lines = (tmp_path / "tnotes.jsonl").read_text().strip().split("\n")
    assert json.loads(lines[0])["id"] == e["id"]

def test_ids_unique(tmp_path, monkeypatch):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    ids = {store.add_entry(type="note", title=f"t{i}", body="b", tags=[],
                           scope="global", cwd=None, show_on_open=True)["id"]
           for i in range(50)}
    assert len(ids) == 50

def test_visible_entries_filters(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    here = os.path.realpath(os.getcwd())
    g = store.add_entry(type="note", title="g", body="g", tags=[], scope="global", cwd=None, show_on_open=True)
    l = store.add_entry(type="note", title="l", body="l", tags=[], scope="local", cwd=here, show_on_open=True)
    o = store.add_entry(type="note", title="o", body="o", tags=[], scope="local", cwd="/elsewhere", show_on_open=True)
    assert {e["id"] for e in store.visible_entries()} == {g["id"], l["id"]}
    assert {e["id"] for e in store.visible_entries(scope="global")} == {g["id"]}
    assert {e["id"] for e in store.visible_entries(scope="local")} == {l["id"]}
    assert {e["id"] for e in store.visible_entries(all_dirs=True)} == {g["id"], l["id"], o["id"]}
    store.update_entry(l["id"], status="done")
    assert l["id"] not in {e["id"] for e in store.visible_entries()}
    assert l["id"] in {e["id"] for e in store.visible_entries(include_done=True)}
    store.update_entry(l["id"], status="active", show_on_open=False)
    assert l["id"] not in {e["id"] for e in store.visible_entries()}
    assert l["id"] in {e["id"] for e in store.visible_entries(include_hidden=True)}
