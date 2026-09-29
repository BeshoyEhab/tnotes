# tests/test_picker.py
from tnotes.picker import format_row, build_rows
from tnotes import store
from tnotes.cli import main

def test_format_row_icons_scope():
    assert format_row({"type": "url", "title": "t", "tags": ["a"], "scope": "global", "status": "active"}).startswith("🔗 t [a] G")
    assert format_row({"type": "cmd", "title": "t", "tags": [], "scope": "local", "status": "active"}).startswith("$ t ·")
    assert "✔" in format_row({"type": "note", "title": "t", "tags": [], "scope": "local", "status": "done"})

def test_build_rows_tab_id():
    rows = build_rows([{"id": "abc123", "type": "note", "title": "hi", "tags": [], "scope": "global", "status": "active"}])
    assert rows[0].endswith("\tabc123")

def test_open_second_action(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="n", body="see https://a.example and https://b.example",
                        tags=[], scope="global", cwd=None, show_on_open=True)
    monkeypatch.setattr("tnotes.cli_actions.actions.open_target", lambda url: (print(url), 0)[1])
    assert main(["open", e["id"], "2"]) == 0
    assert "https://b.example" in capsys.readouterr().out
