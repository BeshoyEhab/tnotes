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

def test_show_startup_silent_when_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    assert main(["show", "--startup"]) == 0
    assert capsys.readouterr().out == ""

def test_preview_caps_100_lines(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    body = "\n".join(f"line {i}" for i in range(150))
    e = store.add_entry(type="note", title="big", body=body, tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert main(["show", e["id"], "--preview"]) == 0
    out = capsys.readouterr().out
    assert "… (+50 lines, Enter for full)" in out
    assert "line 99" in out and "line 100" not in out

def test_list_hides_done_unless_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="t", body="b", tags=[], scope="global", cwd=None, show_on_open=True)
    store.update_entry(e["id"], status="done")
    assert main(["list"]) == 0
    assert e["id"] not in capsys.readouterr().out
    assert main(["list", "--done"]) == 0
    assert e["id"] in capsys.readouterr().out

def test_ambiguous_prefix_rm_deletes_nothing(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    def _ent(eid):
        return {"id": eid, "type": "note", "title": "t", "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": "active",
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("abcdef")) + "\n" + json.dumps(_ent("abc123")) + "\n",
        encoding="utf-8")
    assert main(["rm", "abc"]) == 1
    ids = {e["id"] for e in store.load_all()}
    assert ids == {"abcdef", "abc123"}

def test_open_invalid_index_no_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="t", body="b", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert main(["open", e["id"], "foo"]) == 1
    err = capsys.readouterr().err
    assert "invalid index" in err
