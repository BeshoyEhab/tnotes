# tests/test_cli.py
import os
from pathlib import Path
from tnotes.cli import main, compose_in_editor
from tnotes import actions, store

def _add(capsys, *argv):
    assert main(list(argv)) == 0
    return capsys.readouterr().out

def test_quick_add_defaults_local(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    out = _add(capsys, "buy milk")
    eid = out.strip().split()[-1]
    e = store.get_entry(eid)
    assert e["type"] == "note" and e["scope"] == "local" and e["cwd"] == os.path.realpath(os.getcwd())
    assert e["status"] == "active" and e["show_on_open"] is True

def test_typed_add_global_no_show_tags(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    out = _add(capsys, "--url", "https://x.example", "--title", "t", "-g", "--tags", "a,b", "--no-show")
    e = store.get_entry(out.strip().split()[-1])
    assert (e["type"], e["scope"], e["tags"], e["show_on_open"]) == ("url", "global", ["a", "b"], False)

def test_done_undone_hide_unhide_rm(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    eid = _add(capsys, "tmp").strip().split()[-1]
    assert main(["done", eid]) == 0 and store.get_entry(eid)["status"] == "done"
    assert main(["undone", eid]) == 0 and store.get_entry(eid)["status"] == "active"
    assert main(["hide", eid]) == 0 and store.get_entry(eid)["show_on_open"] is False
    assert main(["unhide", eid]) == 0 and store.get_entry(eid)["show_on_open"] is True
    assert main(["rm", eid]) == 0 and store.get_entry(eid) is None

def test_editor_failure_keeps_draft(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setattr(actions, "edit_in_editor", lambda p: 1)
    assert compose_in_editor("note", "hi") is None
    tmp = capsys.readouterr().out.strip().split()[-1]
    assert Path(tmp).exists()
    e = store.add_entry(type="note", title="t", body="b", tags=[], scope="global", cwd=None, show_on_open=True)
    assert main(["edit", e["id"]]) == 1
    tmp = capsys.readouterr().out.strip().split()[-1]
    assert Path(tmp).exists()
